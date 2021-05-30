import configparser
import sys

from zulip_bots.lib import BotIdentity
from uuid import uuid4

class SimpleStorage:
    def __init__(self):
        self.data = {}

    def contains(self, key):
        return (key in self.data)

    def put(self, key, value):
        self.data[key] = value

    def get(self, key):
        return self.data[key]

class MockMessageServer:
    # This class is needed for the incrementor bot, which
    # actually updates messages!
    def __init__(self):
        self.message_id = 0
        self.messages = {}

    def send(self, message):
        self.message_id += 1
        message['id'] = self.message_id
        self.messages[self.message_id] = message
        return message

    def add_reaction(self, reaction_data):
        return dict(result='success', msg='', uri='https://server/messages/{}/reactions'.format(uuid4()))

    def update(self, message):
        self.messages[message['message_id']] = message

    def upload_file(self, file):
        return dict(result='success', msg='', uri='https://server/user_uploads/{}'.format(uuid4()))

class TerminalBotHandler:
    def __init__(self, bot_config_file, message_server):
        self.bot_config_file = bot_config_file
        self._storage = SimpleStorage()
        self.message_server = message_server

    @property
    def storage(self):
        return self._storage

    def identity(self):
        return BotIdentity("bot name", "bot-email@domain")

    def react(self, message, emoji_name):
        """
        Mock adding an emoji reaction and print it in the terminal.
        """
        print("""The bot reacts to message #{}: {}""".format(message["id"], emoji_name))
        return self.message_server.add_reaction(dict(message_id=message['id'],
                                                     emoji_name=emoji_name,
                                                     reaction_type='unicode_emoji'))

    def send_message(self, message):
        """
        Print the message sent in the terminal and store it in a mock message server.
        """
        if message['type'] == 'stream':
            print('''
                stream: {} topic: {}
                {}
                '''.format(message['to'], message['subject'], message['content']))
        else:
            print('''
                PM response:
                {}
                '''.format(message['content']))
        # Note that message_server is only responsible for storing and assigning an
        # id to the message instead of actually displaying it.
        return self.message_server.send(message)

    def send_reply(self, message, response):
        """
        Print the reply message in the terminal and store it in a mock message server.
        """
        print("\nReply from the bot is printed between the dotted lines:\n-------\n{}\n-------".format(response))
        response_message = dict(
            content=response
        )
        return self.message_server.send(response_message)

    def update_message(self, message):
        """
        Update a previously sent message and print the result in the terminal.
        Throw an IndexError if the message id is invalid.
        """
        self.message_server.update(message)
        print('''
            update to message #{}:
            {}
            '''.format(message['message_id'], message['content']))

    def upload_file_from_path(self, file_path):
        with open(file_path) as file:
            return self.upload_file(file)

    def upload_file(self, file):
        return self.message_server.upload_file(file)

    def get_config_info(self, bot_name, optional=False):
        if self.bot_config_file is None:
            if optional:
                return {}
            else:
                print('Please supply --bot-config-file argument.')
                sys.exit(1)

        config = configparser.ConfigParser()
        with open(self.bot_config_file) as conf:
            config.read_file(conf)

        return dict(config.items(bot_name))
