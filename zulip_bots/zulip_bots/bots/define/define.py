# See readme.md for instructions on running this code.
import logging
import requests
import html2text
import string

from typing import Dict
from zulip_bots.lib import BotHandler

class DefineHandler:
    '''
    This plugin define a word that the user inputs. It
    looks for messages starting with '@mention-bot'.
    '''

    DEFINITION_API_URL = 'https://owlbot.info/api/v2/dictionary/{}?format=json'
    REQUEST_ERROR_MESSAGE = 'Could not load definition.'
    EMPTY_WORD_REQUEST_ERROR_MESSAGE = 'Please enter a word to define.'
    PHRASE_ERROR_MESSAGE = 'Definitions for phrases are not available.'
    SYMBOLS_PRESENT_ERROR_MESSAGE = 'Definitions of words with symbols are not possible.'

    def usage(self) -> str:
        return '''
            This plugin will allow users to define a word. Users should preface
            messages with @mention-bot.
            '''

    def handle_message(self, message: Dict[str, str], bot_handler: BotHandler) -> None:
        original_content = message['content'].strip()
        bot_response = self.get_bot_define_response(original_content)

        bot_handler.send_reply(message, bot_response)

    def get_bot_define_response(self, original_content: str) -> str:
        split_content = original_content.split(' ')
        # If there are more than one word (a phrase)
        if len(split_content) > 1:
            return DefineHandler.PHRASE_ERROR_MESSAGE

        to_define = split_content[0].strip()
        to_define_lower = to_define.lower()

        # Check for presence of non-letters
        non_letters = set(to_define_lower) - set(string.ascii_lowercase)
        if non_letters:
            return self.SYMBOLS_PRESENT_ERROR_MESSAGE

        # No word was entered.
        if not to_define_lower:
            return self.EMPTY_WORD_REQUEST_ERROR_MESSAGE
        else:
            response = '**{}**:\n'.format(to_define)

            try:
                # Use OwlBot API to fetch definition.
                api_result = requests.get(self.DEFINITION_API_URL.format(to_define_lower))
                # Convert API result from string to JSON format.
                definitions = api_result.json()

                # Could not fetch definitions for the given word.
                if not definitions:
                    response += self.REQUEST_ERROR_MESSAGE
                else:  # Definitions available.
                    # Show definitions line by line.
                    for d in definitions:
                        example = d['example'] if d['example'] else '*No example available.*'
                        response += '\n' + '* (**{}**) {}\n&nbsp;&nbsp;{}'.format(d['type'], d['definition'], html2text.html2text(example))

            except Exception:
                response += self.REQUEST_ERROR_MESSAGE
                logging.exception("")

            return response

handler_class = DefineHandler
