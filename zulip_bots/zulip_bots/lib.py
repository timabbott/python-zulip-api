from __future__ import print_function

import logging
import os
import signal
import sys
import time
import re

from six.moves import configparser

from contextlib import contextmanager

if False:
    from mypy_extensions import NoReturn
from typing import Any, Optional, List, Dict
from types import ModuleType

from zulip import Client

def exit_gracefully(signum, frame):
    # type: (int, Optional[Any]) -> None
    sys.exit(0)

def get_bot_logo_path(name):
    # type: str -> Optional[str]
    current_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path_png = os.path.join(
        current_dir, 'bots/{bot_name}/logo.png'.format(bot_name=name))
    logo_path_svg = os.path.join(
        current_dir, 'bots/{bot_name}/logo.svg'.format(bot_name=name))

    if os.path.isfile(logo_path_png):
        return logo_path_png
    elif os.path.isfile(logo_path_svg):
        return logo_path_svg

    return None

def get_bots_directory_path():
    # type: () -> str
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, 'bots')

def get_bot_doc_path(name):
    # type: (str) -> str
    return os.path.join(get_bots_directory_path(), '{}/doc.md'.format(name))

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

class ExternalBotHandler(object):
    def __init__(self, client, root_dir):
        # type: (Client, string) -> None
        # Only expose a subset of our Client's functionality
        user_profile = client.get_profile()
        self._rate_limit = RateLimit(20, 5)
        self._client = client
        self._root_dir = root_dir
        try:
            self.user_id = user_profile['user_id']
            self.full_name = user_profile['full_name']
            self.email = user_profile['email']
        except KeyError:
            logging.error('Cannot fetch user profile, make sure you have set'
                          ' up the zuliprc file correctly.')
            sys.exit(1)

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

    def get_config_info(self, bot_name, section=None, optional=False):
        # type: (str, Optional[str], Optional[bool]) -> Dict[str, Any]
        conf_file_path = os.path.realpath(os.path.join(
            'zulip_bots', 'bots', bot_name, bot_name + '.conf'))
        section = section or bot_name
        config = configparser.ConfigParser()
        try:
            with open(conf_file_path) as conf:
                config.readfp(conf)  # type: ignore
        except IOError:
            if optional:
                return dict()
            raise
        return dict(config.items(section))

    def open(self, filepath):
        # type: (str) -> None
        filepath = os.path.normpath(filepath)
        abs_filepath = os.path.join(self._root_dir, filepath)
        if abs_filepath.startswith(self._root_dir):
            return open(abs_filepath)
        else:
            raise PermissionError("Cannot open file \"{}\". Bots may only access "
                                  "files in their local directory.".format(abs_filepath))

class StateHandler(object):
    def __init__(self):
        # type: () -> None
        self.state_ = None  # type: Any

    def set_state(self, state):
        # type: (Any) -> None
        self.state_ = state

    def get_state(self):
        # type: () -> Any
        return self.state_

    @contextmanager
    def state(self, default):
        # type: (Any) -> Any
        new_state = self.get_state() or default
        yield new_state
        self.set_state(new_state)

def extract_query_without_mention(message, at_mention_bot_name):
    # type: (Dict[str, Any], str) -> str
    """
    If the bot is the first @mention in the message, then this function returns
    the message with the bot's @mention removed.  Otherwise, it returns None.
    This function is being leveraged by two systems; external bot system and embedded bot system.
    This function is being called by:
    1. 'run_message_handler_for_bot' function (zulip_bots/lib.py file in zulip/python-zulip-api
        repository) that executes/runs/calls external bots.
    2. 'consume' function in EmbeddedBotWorker class (zerver/worker/queue_processors.py
        file in zulip/zulip repository) that executes/runs/calls embedded bots.

    Since, this is a general utility function for any working bot, it is planned to be an independent
    function for now. Any refactoring should correctly be reflected in all the bot systems using this
    function.
    """
    bot_mention = r'^@(\*\*{0}\*\*)'.format(at_mention_bot_name)
    start_with_mention = re.compile(bot_mention).match(message['content'])
    if start_with_mention is None:
        return None
    query_without_mention = message['content'][len(start_with_mention.group()):]
    return query_without_mention.lstrip()

def is_private(message, at_mention_bot_id):
    # type: (Dict[str, Any], int) -> bool
    """
    This function is to ensure that the bot doesn't go into infinite loop if the message sender id is
    the same as the id of the bot which is called. This function makes the bot not reply to itself.

    This function is being leveraged by two systems; external bot system and embedded bot system,
    any change/modification in the structure of this should be reflected at other places accordingly.
    For details read "extract_query_without_mention" function docstring.
    """
    if message['type'] == 'private':
        return at_mention_bot_id != message['sender_id']
    return False

def initialize_config_bot(message_handler, bot_handler):
    # type: (Any, Any) -> None
    """
    If a bot has bot-specific configuration settings (both public or private) to be set, then this
    function calls the 'initialize' function which in turn calls 'get_config_info' for bots.

    This function is being leveraged by two systems; external bot system and embedded bot system,
    any change/modification in the structure of this should be reflected at other places accordingly.
    For details read "extract_query_without_mention" function docstring.
    """
    if hasattr(message_handler, 'initialize'):
        message_handler.initialize(bot_handler=bot_handler)

def get_message_content_if_bot_is_called(message, at_mention_bot_name, at_mention_bot_id):
    # type: (Dict[str, Any], str) -> Any
    """
    Check if the bot is called or not; a bot can be called by 2 ways: @mention-botname or private message
    to the bot. Once it is confirmed if a bot is called or not, then we move to the second part of the
    function.
    If the bot is privately messaged, then the message content need not be modified and the bot can directly
    process the entire message content.
    If the bot is called by @mention-botname, then we need to remove @mention-botname for the bot to
    process the rest of the message content.

    This function is being leveraged by two systems; external bot system and embedded bot system,
    any change/modification in the structure of this should be reflected at other places accordingly.
    For details read "extract_query_without_mention" function docstring.
    """
    # is_mentioned is true if the bot is mentioned at ANY position (not necessarily
    # the first @mention in the message).
    is_mentioned = message['is_mentioned']
    is_private_message = is_private(message=message, at_mention_bot_id=at_mention_bot_id)

    # Strip at-mention botname from the message
    if is_mentioned:
        # message['content'] will be None when the bot's @-mention is not at the beginning.
        # In that case, the message shall not be handled.
        message['content'] = extract_query_without_mention(message=message,
                                                           at_mention_bot_name=at_mention_bot_name)
        if message['content'] is None:
            return

    if (is_private_message or is_mentioned):
        return message['content']
    return None

def run_message_handler_for_bot(lib_module, quiet, config_file, bot_name):
    # type: (Any, bool, str) -> Any
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
    initialize_config_bot(message_handler=message_handler, bot_handler=restricted_client)

    state_handler = StateHandler()

    if not quiet:
        print(message_handler.usage())

    def handle_message(message):
        # type: (Dict[str, Any]) -> None
        logging.info('waiting for next message')

        message_content_if_bot_is_called = get_message_content_if_bot_is_called(message=message,
                                                                                at_mention_bot_name=restricted_client.full_name,
                                                                                at_mention_bot_id=restricted_client.user_id)

        if message_content_if_bot_is_called:
            message['content'] = message_content_if_bot_is_called

            message_handler.handle_message(
                message=message,
                bot_handler=restricted_client,
                state_handler=state_handler
            )

    signal.signal(signal.SIGINT, exit_gracefully)

    logging.info('starting message handling...')
    client.call_on_each_message(handle_message)
