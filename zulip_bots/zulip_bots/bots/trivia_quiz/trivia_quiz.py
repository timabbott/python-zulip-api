import html
import json
import requests
import random
import re
from typing import Optional, Any, Dict, Tuple
from zulip_bots.lib import BotHandler

class NotAvailableException(Exception):
    pass

class InvalidAnswerException(Exception):
    pass

class TriviaQuizHandler:
    def usage(self) -> str:
        return '''
            This plugin will give users a trivia question from
            the open trivia database at opentdb.com.'''

    def handle_message(self, message: Dict[str, Any], bot_handler: BotHandler) -> None:
        query = message['content']
        if query == 'new':
            try:
                start_new_quiz(message, bot_handler)
                return
            except NotAvailableException:
                bot_response = 'Uh-Oh! Trivia service is down.'
                bot_handler.send_reply(message, bot_response)
                return
        elif query.startswith('answer'):
            try:
                (quiz_id, answer) = parse_answer(query)
            except InvalidAnswerException:
                bot_response = 'Invalid answer format'
                bot_handler.send_reply(message, bot_response)
                return
            try:
                quiz_payload = get_quiz_from_id(quiz_id, bot_handler)
            except (KeyError, TypeError):
                bot_response = 'Invalid quiz id'
                bot_handler.send_reply(message, bot_response)
                return
            quiz = json.loads(quiz_payload)
            start_new_question, bot_response = handle_answer(quiz, answer, quiz_id,
                                                             bot_handler, message['sender_full_name'])
            bot_handler.send_reply(message, bot_response)
            if start_new_question:
                start_new_quiz(message, bot_handler)
            return
        else:
            bot_response = 'type "new" for a new question'
        bot_handler.send_reply(message, bot_response)

def get_quiz_from_id(quiz_id: str, bot_handler: BotHandler) -> str:
    return bot_handler.storage.get(quiz_id)

def start_new_quiz(message: Dict[str, Any], bot_handler: BotHandler) -> None:
    quiz = get_trivia_quiz()
    quiz_id = generate_quiz_id(bot_handler.storage)
    bot_response = format_quiz_for_markdown(quiz_id, quiz)
    widget_content = format_quiz_for_widget(quiz_id, quiz)
    bot_handler.storage.put(quiz_id, json.dumps(quiz))
    bot_handler.send_reply(message, bot_response, widget_content)

def parse_answer(query: str) -> Tuple[str, str]:
    m = re.match(r'answer\s+(Q...)\s+(.)', query)
    if not m:
        raise InvalidAnswerException()

    quiz_id = m.group(1)
    answer = m.group(2).upper()
    if answer not in 'ABCD':
        raise InvalidAnswerException()

    return (quiz_id, answer)

def get_trivia_quiz() -> Dict[str, Any]:
    payload = get_trivia_payload()
    quiz = get_quiz_from_payload(payload)
    return quiz

def get_trivia_payload() -> Dict[str, Any]:

    url = 'https://opentdb.com/api.php?amount=1&type=multiple'

    try:
        data = requests.get(url)

    except requests.exceptions.RequestException:
        raise NotAvailableException()

    if data.status_code != 200:
        raise NotAvailableException()

    payload = data.json()
    return payload

def fix_quotes(s: str) -> Optional[str]:
    # opentdb is nice enough to escape HTML for us, but
    # we are sending this to code that does that already :)
    #
    # Meanwhile Python took until version 3.4 to have a
    # simple html.unescape function.
    try:
        return html.unescape(s)
    except Exception:
        raise Exception('Please use python3.4 or later for this bot.')

def get_quiz_from_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    result = payload['results'][0]
    question = result['question']
    letters = ['A', 'B', 'C', 'D']
    random.shuffle(letters)
    correct_letter = letters[0]
    answers = {}
    answers[correct_letter] = result['correct_answer']
    for i in range(3):
        answers[letters[i+1]] = result['incorrect_answers'][i]
    answers = {
        letter: fix_quotes(answer)
        for letter, answer
        in answers.items()
    }
    quiz = dict(
        question=fix_quotes(question),
        answers=answers,
        answered_options=[],
        pending=True,
        correct_letter=correct_letter,
    )  # type: Dict[str, Any]
    return quiz

def generate_quiz_id(storage: Any) -> str:
    try:
        quiz_num = storage.get('quiz_id')
    except (KeyError, TypeError):
        quiz_num = 0
    quiz_num += 1
    quiz_num = quiz_num % (1000)
    storage.put('quiz_id', quiz_num)
    quiz_id = 'Q%03d' % (quiz_num,)
    return quiz_id

def format_quiz_for_widget(quiz_id: str, quiz: Dict[str, Any]) -> str:
    widget_type = 'zform'
    question = quiz['question']
    answers = quiz['answers']

    heading = quiz_id + ': ' + question

    def get_choice(letter: str) -> Dict[str, str]:
        answer = answers[letter]
        reply = 'answer ' + quiz_id + ' ' + letter

        return dict(
            type='multiple_choice',
            short_name=letter,
            long_name=answer,
            reply=reply,
        )

    choices = [get_choice(letter) for letter in 'ABCD']

    extra_data = dict(
        type='choices',
        heading=heading,
        choices=choices,
    )

    widget_content = dict(
        widget_type=widget_type,
        extra_data=extra_data,
    )
    payload = json.dumps(widget_content)
    return payload

def format_quiz_for_markdown(quiz_id: str, quiz: Dict[str, Any]) -> str:
    question = quiz['question']
    answers = quiz['answers']
    answer_list = '\n'.join([
        '* **{letter}** {answer}'.format(
            letter=letter,
            answer=answers[letter],
        )
        for letter in 'ABCD'
    ])
    how_to_respond = '''**reply**: answer {quiz_id} <letter>'''.format(quiz_id=quiz_id)

    content = '''
Q: {question}

{answer_list}
{how_to_respond}'''.format(
        question=question,
        answer_list=answer_list,
        how_to_respond=how_to_respond,
    )
    return content

def update_quiz(quiz: Dict[str, Any], quiz_id: str, bot_handler: BotHandler) -> None:
    bot_handler.storage.put(quiz_id, json.dumps(quiz))

def build_response(is_correct: bool, num_answers: int) -> str:
    if is_correct:
        response = ':tada: **{answer}** is correct, {sender_name}!'
    else:
        if num_answers >= 3:
            response = ':disappointed: WRONG, {sender_name}! The correct answer is **{answer}**.'
        else:
            response = ':disappointed: WRONG, {sender_name}! {option} is not correct.'
    return response

def handle_answer(quiz: Dict[str, Any], option: str, quiz_id: str,
                  bot_handler: BotHandler, sender_name: str) -> Tuple[bool, str]:
    answer = quiz['answers'][quiz['correct_letter']]
    is_new_answer = (option not in quiz['answered_options'])
    if is_new_answer:
        quiz['answered_options'].append(option)

    num_answers = len(quiz['answered_options'])
    is_correct = (option == quiz['correct_letter'])

    start_new_question = quiz['pending'] and (is_correct or num_answers >= 3)
    if start_new_question or is_correct:
        quiz['pending'] = False

    if is_new_answer or start_new_question:
        update_quiz(quiz, quiz_id, bot_handler)

    response = build_response(is_correct, num_answers).format(
        option=option, answer=answer, id=quiz_id, sender_name=sender_name)
    return start_new_question, response


handler_class = TriviaQuizHandler
