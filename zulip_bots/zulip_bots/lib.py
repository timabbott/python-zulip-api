import configparser
import json
import logging
import os
import signal
import sys
import time
import re


from contextlib import contextmanager
from typing import Any, Iterator, Optional, List, Dict, IO, Set, Text
from typing_extensions import Protocol
from zulip import Client, ZulipError


class NoBotConfigException(Exception):
    pass


class StateHandlerError(Exception):
    pass


def exit_gracefully(signum: int, frame: Optional[Any]) -> None:
    sys.exit(0)


def get_bots_directory_path() -> str:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, 'bots')

def zulip_env_vars_are_present() -> bool:
    # We generally require a Zulip config file, but if
    # the user supplies the correct environment vars, we
    # waive the requirement.  This can be helpful for
    # containers like Heroku that prefer env vars to config
    # files.
    if os.environ.get('ZULIP_EMAIL') is None:
        return False
    if os.environ.get('ZULIP_API_KEY') is None:
        return False
    if os.environ.get('ZULIP_SITE') is None:
        return False

    # If none of the absolutely critical env vars are
    # missing, we can proceed without a config file.
    return True

class RateLimit:
    def __init__(self, message_limit: int, interval_limit: int) -> None:
        self.message_limit = message_limit
        self.interval_limit = interval_limit
        self.message_list = []  # type: List[float]
        self.error_message = '-----> !*!*!*MESSAGE RATE LIMIT REACHED, EXITING*!*!*! <-----\n'
        'Is your bot trapped in an infinite loop by reacting to its own messages?'

    def is_legal(self) -> bool:
        self.message_list.append(time.time())
        if len(self.message_list) > self.message_limit:
            self.message_list.pop(0)
            time_diff = self.message_list[-1] - self.message_list[0]
            return time_diff >= self.interval_limit
        else:
            return True

    def show_error_and_exit(self) -> None:
        logging.error(self.error_message)
        sys.exit(1)

class BotIdentity:
    def __init__(self, name: str, email: str) -> None:
        self.name = name
        self.email = email
        self.mention = '@**' + name + '**'

class BotStorage(Protocol):
    def put(self, key: Text, value: Any) -> None:
        ...

    def get(self, key: Text) -> Any:
        ...

    def contains(self, key: Text) -> bool:
        ...

class CachedStorage:
    def __init__(self, parent_storage: BotStorage, init_data: Dict[str, Any]) -> None:
        # CachedStorage is implemented solely for the context manager of any BotHandler.
        # It has a parent_storage that is responsible of communicating with the database
        #   1. when certain data is not cached;
        #   2. when the data need to be flushed to the database.
        # It can be initialized with the given data.
        self._parent_storage = parent_storage
        self._cache = init_data
        self._dirty_keys: Set[str] = set()

    def put(self, key: Text, value: Any) -> None:
        # In the cached storage, values being put to the storage is not flushed to the parent storage.
        # It will be marked dirty until it get flushed.
        self._cache[key] = value
        self._dirty_keys.add(key)

    def get(self, key: Text) -> Any:
        # Unless the key is not found in the cache, the cached storage will not lookup the parent storage.
        if key in self._cache:
            return self._cache[key]
        else:
            value = self._parent_storage.get(key)
            self._cache[key] = value
            return value

    def flush(self) -> None:
        # Flush the data to the parent storage.
        # Data that are not marked dirty will be omitted.
        # This should be manually called when CachedStorage is not used with a context manager.
        while len(self._dirty_keys) > 0:
            key = self._dirty_keys.pop()
            self._parent_storage.put(key, self._cache[key])

    def flush_one(self, key: Text) -> None:
        self._dirty_keys.remove(key)
        self._parent_storage.put(key, self._cache[key])

    def contains(self, key: Text) -> bool:
        if key in self._cache:
            return True
        else:
            return self._parent_storage.contains(key)

class StateHandler:
    def __init__(self, client: Client) -> None:
        self._client = client
        self.marshal = lambda obj: json.dumps(obj)
        self.demarshal = lambda obj: json.loads(obj)
        self.state_ = {}  # type: Dict[Text, Any]

    def put(self, key: Text, value: Any) -> None:
        self.state_[key] = self.marshal(value)
        response = self._client.update_storage({'storage': {key: self.state_[key]}})
        if response['result'] != 'success':
            raise StateHandlerError("Error updating state: {}".format(str(response)))

    def get(self, key: Text) -> Any:
        if key in self.state_:
            return self.demarshal(self.state_[key])

        response = self._client.get_storage({'keys': [key]})
        if response['result'] != 'success':
            raise KeyError('key not found: ' + key)

        marshalled_value = response['storage'][key]
        self.state_[key] = marshalled_value
        return self.demarshal(marshalled_value)

    def contains(self, key: Text) -> bool:
        return key in self.state_

@contextmanager
def use_storage(storage: BotStorage, keys: List[Text]) -> Iterator[BotStorage]:
    # The context manager for StateHandler that minimizes the number of round-trips to the server.
    # It will fetch all the data using the specified keys and store them to
    # a CachedStorage that will not communicate with the server until manually
    # calling flush or getting some values that are not previously fetched.
    data = {key: storage.get(key) for key in keys}
    cache = CachedStorage(storage, data)
    yield cache
    cache.flush()

class BotHandler(Protocol):

    user_id: int
    email: str
    full_name: str

    @property
    def storage(self) -> BotStorage:
        ...

    def identity(self) -> BotIdentity:
        ...

    def react(self, message: Dict[str, Any], emoji_name: str) -> Dict[str, Any]:
        ...

    def send_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ...

    def send_reply(self, message: Dict[str, Any], response: str, widget_content: Optional[str] = None) -> Optional[Dict[str, Any]]:
        ...

    def update_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ...

    def get_config_info(self, bot_name: str, optional: bool = False) -> Dict[str, str]:
        ...

    def quit(self, message: str = "") -> None:
        ...

class ExternalBotHandler:
    def __init__(
        self,
        client: Client,
        root_dir: str,
        bot_details: Dict[str, Any],
        bot_config_file: Optional[str] = None,
        bot_config_parser: Optional[configparser.ConfigParser] = None,
    ) -> None:
        # Only expose a subset of our Client's functionality
        try:
            user_profile = client.get_profile()
        except ZulipError as e:
            print('''
                ERROR: {}

                Have you not started the server?
                Or did you mis-specify the URL?
                '''.format(e))
            sys.exit(1)

        if user_profile.get('result') == 'error':
            msg = user_profile.get('msg', 'unknown')
            print('''
                ERROR: {}
                '''.format(msg))
            sys.exit(1)

        self._rate_limit = RateLimit(20, 5)
        self._client = client
        self._root_dir = root_dir
        self.bot_details = bot_details
        self.bot_config_file = bot_config_file
        self._bot_config_parser = bot_config_parser
        self._storage = StateHandler(client)
        try:
            self.user_id = user_profile['user_id']
            self.full_name = user_profile['full_name']
            self.email = user_profile['email']
        except KeyError:
            logging.error('Cannot fetch user profile, make sure you have set'
                          ' up the zuliprc file correctly.')
            sys.exit(1)

    @property
    def storage(self) -> StateHandler:
        return self._storage

    def identity(self) -> BotIdentity:
        return BotIdentity(self.full_name, self.email)

    def react(self, message: Dict[str, Any], emoji_name: str) -> Dict[str, Any]:
        return self._client.add_reaction(dict(message_id=message['id'],
                                              emoji_name=emoji_name,
                                              reaction_type='unicode_emoji'))

    def send_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        if not self._rate_limit.is_legal():
            self._rate_limit.show_error_and_exit()
        resp = self._client.send_message(message)
        if resp.get('result') == 'error':
            print("ERROR!: " + str(resp))
        return resp

    def send_reply(self, message: Dict[str, Any], response: str, widget_content: Optional[str] = None) -> Dict[str, Any]:
        if message['type'] == 'private':
            return self.send_message(dict(
                type='private',
                to=[x['id'] for x in message['display_recipient']],
                content=response,
                widget_content=widget_content,
            ))
        else:
            return self.send_message(dict(
                type='stream',
                to=message['display_recipient'],
                subject=message['subject'],
                content=response,
                widget_content=widget_content,
            ))

    def update_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        if not self._rate_limit.is_legal():
            self._rate_limit.show_error_and_exit()
        return self._client.update_message(message)

    def get_config_info(self, bot_name: str, optional: bool = False) -> Dict[str, str]:
        if self._bot_config_parser is not None:
            config_parser = self._bot_config_parser
        else:
            if self.bot_config_file is None:
                if optional:
                    return {}

                # Well written bots should catch this exception
                # and provide nice error messages with instructions
                # on setting up the configuration specfic to this bot.
                # And then `run.py` should also catch exceptions on how
                # to specify the file in the command line.
                raise NoBotConfigException(bot_name)

            if bot_name not in self.bot_config_file:
                print('''
                    WARNING!

                    {} does not adhere to the
                    file naming convention, and it could be a
                    sign that you passed in the
                    wrong third-party configuration file.

                    The suggested name is {}.conf

                    We will proceed anyway.
                    '''.format(self.bot_config_file, bot_name))

            # We expect the caller to pass in None if the user does
            # not specify a bot_config_file.  If they pass in a bogus
            # filename, we'll let an IOError happen here.  Callers
            # like `run.py` will do the command line parsing and checking
            # for the existence of the file.
            config_parser = configparser.ConfigParser()
            with open(self.bot_config_file) as conf:
                try:
                    config_parser.read_file(conf)
                except configparser.Error as e:
                    display_config_file_errors(str(e), self.bot_config_file)
                    sys.exit(1)

        return dict(config_parser.items(bot_name))

    def upload_file_from_path(self, file_path: str) -> Dict[str, Any]:
        with open(file_path, 'rb') as file:
            return self.upload_file(file)

    def upload_file(self, file: IO[Any]) -> Dict[str, Any]:
        if not self._rate_limit.is_legal():
            self._rate_limit.show_error_and_exit()
        return self._client.upload_file(file)

    def open(self, filepath: str) -> IO[str]:
        filepath = os.path.normpath(filepath)
        abs_filepath = os.path.join(self._root_dir, filepath)
        if abs_filepath.startswith(self._root_dir):
            return open(abs_filepath)
        else:
            raise PermissionError("Cannot open file \"{}\". Bots may only access "
                                  "files in their local directory.".format(abs_filepath))

    def quit(self, message: str = "") -> None:
        sys.exit(message)


def extract_query_without_mention(message: Dict[str, Any], client: BotHandler) -> Optional[str]:
    """
    If the bot is the first @mention in the message, then this function returns
    the stripped message with the bot's @mention removed.  Otherwise, it returns None.
    """
    content = message['content']
    mention = '@**' + client.full_name + '**'
    extended_mention_regex = re.compile(r'^@\*\*.*\|' + str(client.user_id) + r'\*\*')
    extended_mention_match = extended_mention_regex.match(content)

    if extended_mention_match:
        return content[extended_mention_match.end():].lstrip()

    if content.startswith(mention):
        return content[len(mention):].lstrip()

    return None


def is_private_message_but_not_group_pm(message_dict: Dict[str, Any], current_user: BotHandler) -> bool:
    """
    Checks whether a message dict represents a PM from another user.

    This function is used by the embedded bot system in the
    zulip/zulip project, so refactor with care.  See the comments in
    extract_query_without_mention.
    """
    if not message_dict['type'] == 'private':
        return False
    is_message_from_self = current_user.user_id == message_dict['sender_id']
    recipients = [x['email'] for x in message_dict['display_recipient'] if current_user.email != x['email']]
    return len(recipients) == 1 and not is_message_from_self


def display_config_file_errors(error_msg: str, config_file: str) -> None:
    file_contents = open(config_file).read()
    print('\nERROR: {} seems to be broken:\n\n{}'.format(config_file, file_contents))
    print('\nMore details here:\n\n{}\n'.format(error_msg))


def prepare_message_handler(bot: str, bot_handler: BotHandler, bot_lib_module: Any) -> Any:
    message_handler = bot_lib_module.handler_class()
    if hasattr(message_handler, 'validate_config'):
        config_data = bot_handler.get_config_info(bot)
        bot_lib_module.handler_class.validate_config(config_data)
    if hasattr(message_handler, 'initialize'):
        message_handler.initialize(bot_handler=bot_handler)
    return message_handler


def run_message_handler_for_bot(
    lib_module: Any,
    quiet: bool,
    config_file: str,
    bot_config_file: str,
    bot_name: str,
) -> Any:
    """
    lib_module is of type Any, since it can contain any bot's
    handler class. Eventually, we want bot's handler classes to
    inherit from a common prototype specifying the handle_message
    function.

    Set default bot_details, then override from class, if provided
    """
    bot_details = {
        'name': bot_name.capitalize(),
        'description': "",
    }
    bot_details.update(getattr(lib_module.handler_class, 'META', {}))
    # Make sure you set up your ~/.zuliprc

    client_name = "Zulip{}Bot".format(bot_name.capitalize())

    try:
        client = Client(config_file=config_file, client=client_name)
    except configparser.Error as e:
        display_config_file_errors(str(e), config_file)
        sys.exit(1)

    bot_dir = os.path.dirname(lib_module.__file__)
    restricted_client = ExternalBotHandler(client, bot_dir, bot_details, bot_config_file)

    message_handler = prepare_message_handler(bot_name, restricted_client, lib_module)

    if not quiet:
        print("Running {} Bot:".format(bot_details['name']))
        if bot_details['description'] != "":
            print("\n\t{}".format(bot_details['description']))
        if hasattr(message_handler, 'usage'):
            print(message_handler.usage())
        else:
            print('WARNING: {} is missing usage handler, please add one eventually'.format(bot_name))

    def handle_message(message: Dict[str, Any], flags: List[str]) -> None:
        logging.info('waiting for next message')
        # `mentioned` will be in `flags` if the bot is mentioned at ANY position
        # (not necessarily the first @mention in the message).
        is_mentioned = 'mentioned' in flags
        is_private_message = is_private_message_but_not_group_pm(message, restricted_client)

        # Provide bots with a way to access the full, unstripped message
        message['full_content'] = message['content']
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

    def event_callback(event: Dict[str, Any]) -> None:
        if event['type'] == 'message':
            handle_message(event['message'], event['flags'])

    client.call_on_each_event(event_callback, ['message'])
