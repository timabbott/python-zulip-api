# See readme.md for instructions on running this code.

from __future__ import absolute_import
from __future__ import print_function
from six.moves import range

from collections import OrderedDict, namedtuple

def input_from_message_content(message_content):
    # Translate message content into expected input form
    # (validation is dependent upon the command)
    lines = message_content.split('\n')
    main_line = lines[0].split(' ')
    command = main_line[0]
    options = main_line[1:]
    title   = ""
    if len(lines) > 1:
        title = lines[1]
    vote_options = []
    if len(lines) > 2:
        vote_options = lines[2:]
    vote_options = [v for v in vote_options if len(v) > 0]
    Input = namedtuple('Input', ['command', 'options', 'title', 'vote_options'])
    return Input(command, options, title, vote_options)

help_msg = OrderedDict([
    ('about', "gives a simple summary of this bot."),
    ('help', "produces this help."),
    ('commands', "a concise form of help, listing the supported commands."),
    ('new', ("start a new poll: specify a title on the following line "
             "and at least two options on subsequent lines.")),
    ('vote', ("vote in an ongoing poll: specify a poll id given in the poll message "
              "followed by the number of the option to vote for.")),
    ('end', ("end your own ongoing poll.")),
])

PollTuple = namedtuple('PollTuple', ['stream', 'topic', 'id'])

stream_topic_notgiven = "\nPlease specify a stream & topic if messaging the bot privately."
space_equivalent = "+"

class InvalidInput(Exception):
    pass

def poll_context(poll_tuple, poll):
    return (" on stream '#{}' (topic '{}') titled: '{}'"
            .format(poll_tuple.stream, poll_tuple.topic, poll['title']))

def validate_new_input(inputs, message, active_polls):
    # (Input, Dict[str, Any], Dict[str, Any]) -> PollTuple
    # Validate inputs to new command, raising InvalidInput or returning poll_tuple.
    sender = message["sender_email"]
    sender_id = message["sender_id"]
    # Check input.options and set poll_tuple
    if message['type'] == 'private':
        if len(inputs.options) != 2:
            raise InvalidInput(stream_topic_notgiven)
        else:
            stream = inputs.options[0].replace(space_equivalent, " ")
            topic = inputs.options[1].replace(space_equivalent, " ")
            poll_tuple = PollTuple(stream, topic, sender_id)
    else:
        poll_tuple = PollTuple(message['display_recipient'], message['subject'], sender_id)
    # Check if a poll is already active with this id
    if poll_tuple in active_polls:
        raise InvalidInput(("You already have a poll running{}; end it explicitly first."
                            .format(poll_context(poll_tuple, active_polls[poll_tuple]))))
    # Check we have at least a poll title and 2(+) vote_options
    if inputs.title == "" or len(inputs.vote_options) < 2:
        raise InvalidInput("To " + help_msg['new'])  # FIXME improve message?
    return poll_tuple

def validate_vote_input(inp, message, active_polls):
    # (Input, Dict[str, Any], Dict[str, Any]) -> (PollTuple, int)
    # Validate inputs to vote command, raising InvalidInput,
    # or returning PollTuple and the index into the votes to increment.
    sender_id = message["sender_id"]
    # Use inp.options to make 1st guess of poll_tuple, poll_id and vote_index
    if message['type'] == 'private':
        if len(inp.options) != 4:
            raise InvalidInput("To " + help_msg['vote'] + stream_topic_notgiven)
        else:
            poll_id = inp.options[2]
            vote_index = inp.options[3]
            stream = inp.options[0].replace(space_equivalent, " ")
            topic = inp.options[1].replace(space_equivalent, " ")
            poll_tuple = PollTuple(stream, topic, poll_id)
    else:
        if len(inp.options) != 2:
            raise InvalidInput("To " + help_msg['vote'])
        else:
            poll_id = inp.options[0]
            vote_index = inp.options[1]
            poll_tuple = PollTuple(message['display_recipient'],
                                   message['subject'], poll_id)
    # Update poll_tuple to ensure poll_id is an int
    try:
        poll_tuple = PollTuple(poll_tuple.stream, poll_tuple.topic, int(poll_id))
    except ValueError:
        raise InvalidInput("To " + help_msg['vote'])  # FIXME Improve message - id is not an int!
    # Confirm poll_tuple relates to an active poll
    poll = active_polls.get(poll_tuple)
    if poll is None:
        raise InvalidInput("To " + help_msg['vote'])  # FIXME Improve message - no poll exists!
    # Ensure user has not voted in this poll already
    for i, tally in enumerate(poll['tallies']):
        if sender_id in tally:
            msg = ("You have already voted in the poll{}\n(You voted for: {}. {})"
                   .format(poll_context(poll_tuple, poll), i+1, poll[i]))
            raise InvalidInput(msg)
    # Check that vote_index is an int and within expected bounds
    try:
        vote_index = int(vote_index)
    except ValueError:
        raise InvalidInput("Please select one **number** to vote for in the poll{}"
                           .format(poll_context(poll_tuple, poll)))
    if not (0 < vote_index <= poll['n']):  # Indexed from 1
        raise InvalidInput("Please select a number to vote for, **between 1-{}**, in the poll{}"
                       .format(poll['n'], poll_context(poll_tuple, poll)))
    return (poll_tuple, vote_index)

def validate_end_input(inp, message, active_polls):
    # (Input, Dict[str, Any], Dict[str, Any]) -> PollTuple
    # Validate inputs to end command, raising InvalidInput or returning poll_tuple.
    sender_id = message["sender_id"]
    # Check input.options and set poll_tuple
    if message['type'] == 'private':
        if len(inp.options) != 2:
            raise InvalidInput(stream_topic_notgiven)
        else:
            stream = inp.options[0].replace(space_equivalent, " ")
            topic = inp.options[1].replace(space_equivalent, " ")
            poll_tuple = PollTuple(stream, topic, sender_id)
    else:
        poll_tuple = PollTuple(message['display_recipient'], message['subject'], sender_id)
    # Check the poll that the user wants to end exists already
    if poll_tuple not in active_polls:
        raise InvalidInput("You do not have a poll in '#{}' and topic '{}'"
                           .format(poll_tuple.stream, poll_tuple.topic))
    return poll_tuple

def poll_text_from_poll(poll):
    # (Dict[str, Any]) -> Text
    # Given a poll, generate the text which appears in the message.
    msg = ("Poll by {} (id: {})\n{}\n"
           .format(poll['creator'], poll['creator_id'], poll['title']))
    for i in range(poll['n']):
        msg += ("{}. [{}] {}\n"
                .format(i+1, len(poll['tallies'][i]), poll[i]))
    return msg


class PollHandler(object):
    def usage(self):
        return '''
            This bot maintains up to one poll per user, per topic, in streams only.
            It currently keeps a running count of the votes, as they are made, with one
            mesage in the stream being updated to show the current status.
            Message the bot privately, appending the stream and topic, or mention it
            within a topic (for new, vote and end commands); if the stream or
            topic contain spaces use a '+' where the space would be.
            '''

    def handle_message(self, message, bot_handler, state_handler):

        sender = message["sender_email"]

        def private_reply(text):
            # (Text) -> None
            bot_handler.send_message(dict(type='private', to=sender, content=str(text)))

        def update_poll_text(poll, poll_tuple, force_end=False):
            # (Dict[str, Any], PollTuple, bool) -> (Text, bool)
            poll_text = "{}{}".format(poll_text_from_poll(poll),
                                      "**This poll has ended**\n" if force_end else "")
            if poll['msg_id'] is None:
                result = bot_handler.send_message(dict(type='stream',
                                                       to=poll_tuple.stream,
                                                       subject=poll_tuple.topic,
                                                       content=poll_text))
                if result['result'] == 'success':
                    poll['msg_id'] = result['id']
            else:
                result = bot_handler.update_message(dict(message_id = poll['msg_id'],
                                                         content = poll_text))
            return (poll_text, 'success' == result['result'])

        # Break down the text supplied into potential input
        inp = input_from_message_content(message['content'])

        # Simple commands with no state
        if inp.command == "" or inp.command == "help":
            private_reply("{}\n\nIt supports the following commands:\n\n{}"
                          .format(" ".join(self.usage().split()),
                                  "\n".join("**{}** : {}".format(k,v)
                                            for k, v in help_msg.items())))
            return
        elif inp.command == "about":
            private_reply(" ".join(self.usage().split()))
            return
        elif inp.command == "commands":
            private_reply("Commands: " + ", ".join((k for k in help_msg)))
            return
        elif inp.command not in ('new', 'vote', 'end'):
            private_reply("Unsupported command '{}'.".format(inp.command))
            return

        # We now have commands using state, so ensure we have some
        with state_handler.state({}) as active_polls:

            if inp.command == "new":
                try:
                    poll_tuple = validate_new_input(inp, message, active_polls)
                except InvalidInput as e:
                    private_reply(e)
                    return

                # Create new poll data
                new_poll = {
                    'title': inp.title,  # Poll title
                    'tallies': [],   # List of list of sender_id's who voted
                    'msg_id': None,  # Message id with poll text (to update)
                    'n': len(inp.vote_options),  # How many voting options
                    'creator': message['sender_full_name'],  # Name of poll creator
                    'creator_id': poll_tuple.id,
                }
                for i, v in enumerate(inp.vote_options):  # Set text & tallies for each vote_option
                    new_poll[i] = v
                    new_poll['tallies'].append([])

                # Try to send initial poll message to stream/topic, and alert user of result
                (update_msg, success) = update_poll_text(new_poll, poll_tuple)
                if success:
                    active_polls[poll_tuple] = new_poll
                    msg = ("Poll created in stream '#{}' with topic '{}':\n{}"
                           .format(poll_tuple.stream, poll_tuple.topic, update_msg))
                else:
                    msg = ("Could not create poll in stream '#{}' with topic '{}'"
                           .format(poll_tuple.stream, poll_tuple.topic))

            elif inp.command == "vote":
                try:
                    (poll_tuple, vote_index) = validate_vote_input(inp, message, active_polls)
                except InvalidInput as e:
                    private_reply(e)
                    return

                # Use the vote
                poll = active_polls[poll_tuple]
                poll['tallies'][vote_index-1].append(message['sender_id'])

                # Try to update poll message to stream/topic, and alert user of result
                (update_msg, success) = update_poll_text(poll, poll_tuple)
                if success:
                    msg = ("You just voted in the poll{}\n(You voted for: {}. {})"
                           .format(poll_context(poll_tuple, poll), vote_index, poll[vote_index-1]))
                else:
                    msg = "**Could not update the poll with your vote.**"
                    # FIXME Should we end the poll automatically here? roll-back data?

            elif inp.command == "end":
                try:
                    poll_tuple = validate_end_input(inp, message, active_polls)
                except InvalidInput as e:
                    private_reply(e)
                    return

                # Try to update poll message to be ended, and end the poll
                (update_msg, success) = update_poll_text(active_polls[poll_tuple],
                                                         poll_tuple, force_end=True)
                msg = (("Ending your poll in '#{}' and topic '{}'; "
                       "final results were:\n\n{}")
                       .format(poll_tuple.stream, poll_tuple.topic, update_msg[:-1]))
                if not success:
                    msg += ("NOTE: Your poll ended, but the poll message could not be updated.")
                del active_polls[poll_tuple]

            private_reply(msg)


handler_class = PollHandler
