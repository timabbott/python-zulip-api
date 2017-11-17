from __future__ import print_function

import json
import logging
import os
import signal
import sys
import time
import re

from six.moves import configparser

from contextlib import contextmanager

from collections import namedtuple

if False:
    from mypy_extensions import NoReturn
from typing import Any, Optional, List, Dict, IO, Text, NamedTuple
from types import ModuleType

from zulip import Client

def exit_gracefully(signum, frame):
    # type: (int, Optional[Any]) -> None
    sys.exit(0)

def get_bots_directory_path():
    # type: () -> str
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, 'bots')

class RateLimit(object):
    def __init__(self, message_limit, interval_limit):
        # type: (int, int) -> None
        self.message_limit = message_limit
        self.interval_limit = interval_limit
        self.message_list = []  # type: List[float]
        self.error_message = '-----> !*!*!*MESSAGE RATE LIMIT REACHED, EXITING*!*!*! <-----\n'
        'Is your bot trapped in an infinite loop by reacting to its own messages?'

    def is_legal(self):
        # type: () -> bool
        self.message_list.append(time.time())
        if len(self.message_list) > self.message_limit:
            self.message_list.pop(0)
            time_diff = self.message_list[-1] - self.message_list[0]
            return time_diff >= self.interval_limit
        else:
            return True

    def show_error_and_exit(self):
        # type: () -> NoReturn
        logging.error(self.error_message)
        sys.exit(1)

class StateHandler(object):
    def __init__(self):
        # type: () -> None
        self.state_ = {}  # type: Dict[Text, Text]
        self.marshal = lambda obj: obj
        self.demarshal = lambda obj: obj

    def put(self, key, value):
        # type: (Text, Text) -> None
        self.state_[key] = self.marshal(value)

    def get(self, key):
        # type: (Text) -> Text
        return self.demarshal(self.state_[key])

    def contains(self, key):
        # type: (Text) -> bool
        return key in self.state_

class ExternalBotHandler(object):
    def __init__(self, client, root_dir):
        # type: (Client, str) -> None
        # Only expose a subset of our Client's functionality
        user_profile = client.get_profile()
        self._rate_limit = RateLimit(20, 5)
        self._client = client
        self._root_dir = root_dir
        self.storage = StateHandler()
        try:
            self.user_id = user_profile['user_id']
            self.full_name = user_profile['full_name']
            self.email = user_profile['email']
        except KeyError:
            logging.error('Cannot fetch user profile, make sure you have set'
                          ' up the zuliprc file correctly.')
            sys.exit(1)

    BotIdentity = namedtuple('BotIdentity', ['name', 'quoted_name', 'email'])

    def identity(self):
        # type: () -> NamedTuple
        pad = '**' if ' ' in self.full_name else ''
        return BotIdentity(self.full_name,
                           "{0}{1}{0}".format(pad, self.full_name),
                           self.email)

    def send_message(self, message):
        # type: (Dict[str, Any]) -> Dict[str, Any]
        if self._rate_limit.is_legal():
            return self._client.send_message(message)
        else:
            self._rate_limit.show_error_and_exit()

    def send_reply(self, message, response):
        # type: (Dict[str, Any], str) -> Dict[str, Any]
        if message['type'] == 'private':
            return self.send_message(dict(
                type='private',
                to=[x['email'] for x in message['display_recipient'] if self.email != x['email']],
                content=response,
            ))
        else:
            return self.send_message(dict(
                type='stream',
                to=message['display_recipient'],
                subject=message['subject'],
                content=response,
            ))

    def update_message(self, message):
        # type: (Dict[str, Any]) -> Dict[str, Any]
        if self._rate_limit.is_legal():
            return self._client.update_message(message)
        else:
            self._rate_limit.show_error_and_exit()

    def get_config_info(self, bot_name, optional=False):
        # type: (str, Optional[bool]) -> Dict[str, Any]
        conf_file_path = os.path.realpath(os.path.join(self._root_dir, bot_name + '.conf'))
        config = configparser.ConfigParser()
        try:
            with open(conf_file_path) as conf:
                config.readfp(conf)  # type: ignore # readfp->read_file in python 3, so not in stubs
        except IOError:
            if optional:
                return dict()
            raise
        return dict(config.items(bot_name))

    def open(self, filepath):
        # type: (str) -> IO[str]
        filepath = os.path.normpath(filepath)
        abs_filepath = os.path.join(self._root_dir, filepath)
        if abs_filepath.startswith(self._root_dir):
            return open(abs_filepath)
        else:
            raise PermissionError("Cannot open file \"{}\". Bots may only access "
                                  "files in their local directory.".format(abs_filepath))

def extract_query_without_mention(message, client):
    # type: (Dict[str, Any], ExternalBotHandler) -> str
    """
    If the bot is the first @mention in the message, then this function returns
    the stripped message with the bot's @mention removed.  Otherwise, it returns None.
    """
    mention = '@**' + client.full_name + '**'
    if not message['content'].startswith(mention):
        return None
    return message['content'][len(mention):].lstrip()

def is_private_message_from_another_user(message_dict, current_user_id):
    # type: (Dict[str, Any], int) -> bool
    """
    Checks whether a message dict represents a PM from another user.

    This function is used by the embedded bot system in the
    zulip/zulip project, so refactor with care.  See the comments in
    extract_query_without_mention.
    """
    if message_dict['type'] == 'private':
        return current_user_id != message_dict['sender_id']
    return False

def run_message_handler_for_bot(lib_module, quiet, config_file, bot_name):
    # type: (Any, bool, str, str) -> Any
    #
    # lib_module is of type Any, since it can contain any bot's
    # handler class. Eventually, we want bot's handler classes to
    # inherit from a common prototype specifying the handle_message
    # function.
    #
    # Make sure you set up your ~/.zuliprc
    client = Client(config_file=config_file, client="Zulip{}Bot".format(bot_name.capitalize()))
    bot_dir = os.path.dirname(lib_module.__file__)
    restricted_client = ExternalBotHandler(client, bot_dir)

    message_handler = lib_module.handler_class()
    if hasattr(message_handler, 'initialize'):
        message_handler.initialize(bot_handler=restricted_client)

    # Set default bot_details, then override from class, if provided
    bot_details = {
        'name': bot_name.capitalize(),
        'description': "",
    }
    bot_details.update(getattr(lib_module.handler_class, 'META', {}))

    if not quiet:
        print("Running {} Bot:".format(bot_details['name']))
        if bot_details['description'] != "":
            print("\n\t{}".format(bot_details['description']))
        print(message_handler.usage())

    def handle_message(message, flags):
        # type: (Dict[str, Any], List[str]) -> None
        logging.info('waiting for next message')

        # `mentioned` will be in `flags` if the bot is mentioned at ANY position
        # (not necessarily the first @mention in the message).
        is_mentioned = 'mentioned' in flags
        is_private_message = is_private_message_from_another_user(message, restricted_client.user_id)

        # Strip at-mention botname from the message
        if is_mentioned:
            # message['content'] will be None when the bot's @-mention is not at the beginning.
            # In that case, the message shall not be handled.
            message['content'] = extract_query_without_mention(message=message, client=restricted_client)
            if message['content'] is None:
                return

        if is_private_message or is_mentioned:
            message_handler.handle_message(
                message=message,
                bot_handler=restricted_client
            )

    signal.signal(signal.SIGINT, exit_gracefully)

    logging.info('starting message handling...')

    def event_callback(event):
        # type: (Dict[str, Any]) -> None
        if event['type'] == 'message':
            handle_message(event['message'], event['flags'])

    client.call_on_each_event(event_callback, ['message'])
