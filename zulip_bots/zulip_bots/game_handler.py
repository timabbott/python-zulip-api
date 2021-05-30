import json
import re
import random
import logging
from zulip_bots.lib import BotHandler
from copy import deepcopy
from typing import Any, Dict, Tuple, List


class BadMoveException(Exception):
    def __init__(self, message: str) -> None:
        self.message = message

    def __str__(self) -> str:
        return self.message

class SamePlayerMove(Exception):
    def __init__(self, message: str) -> None:
        self.message = message

    def __str__(self) -> str:
        return self.message

class GameAdapter:
    '''
    Class that serves as a template to easily
    create multiplayer games.
    This class handles all commands, and creates
    GameInstances which run the actual game logic.
    '''

    def __init__(
        self,
        game_name: str,
        bot_name: str,
        move_help_message: str,
        move_regex: str,
        model: Any,
        gameMessageHandler: Any,
        rules: str,
        max_players: int = 2,
        min_players: int = 2,
        supports_computer: bool = False
    ) -> None:
        self.game_name = game_name
        self.bot_name = bot_name
        self.move_help_message = move_help_message
        self.move_regex = re.compile(move_regex)
        self.model = model
        self.max_players = max_players
        self.min_players = min_players
        self.is_single_player = self.min_players == self.max_players == 1
        self.supports_computer = supports_computer
        self.gameMessageHandler = gameMessageHandler()
        self.invites = {}  # type: Dict[str, Dict[str, str]]
        self.instances = {}  # type: Dict[str, Any]
        self.user_cache = {}  # type: Dict[str, Dict[str, Any]]
        self.pending_subject_changes = []  # type: List[str]
        self.stream = 'games'
        self.rules = rules

    # Values are [won, lost, drawn, total] new values can be added, but MUST be added to the end of the list.
    def add_user_statistics(self, user: str, values: Dict[str, int]) -> None:
        self.get_user_cache()
        current_values = {}  # type: Dict[str, int]
        if 'stats' in self.get_user_by_email(user).keys():
            current_values = self.user_cache[user]['stats']
        for key, value in values.items():
            if key not in current_values.keys():
                current_values.update({key: 0})
            current_values[key] += value
        self.user_cache[user].update({'stats': current_values})
        self.put_user_cache()

    def help_message(self) -> str:
        return '''** {} Bot Help:**
*Preface all commands with @**{}***
* To start a game in a stream (*recommended*), type
`start game`
* To start a game against another player, type
`start game with @<player-name>`{}
* To play game with the current number of players, type
`play game`
* To quit a game at any time, type
`quit`
* To end a game with a draw, type
`draw`
* To forfeit a game, type
`forfeit`
* To see the leaderboard, type
`leaderboard`
* To withdraw an invitation, type
`cancel game`
* To see rules of this game, type
`rules`
{}'''.format(self.game_name, self.get_bot_username(), self.play_with_computer_help(), self.move_help_message)

    def help_message_single_player(self) -> str:
        return '''** {} Bot Help:**
*Preface all commands with @**{}***
* To start a game in a stream, type
`start game`
* To quit a game at any time, type
`quit`
* To see rules of this game, type
`rules`
{}'''.format(self.game_name, self.get_bot_username(), self.move_help_message)

    def get_commands(self) -> Dict[str, str]:
        action = self.help_message_single_player()
        return {
            'accept': action,
            'decline': action,
            'register': action,
            'draw': action,
            'forfeit': action,
            'leaderboard': action,
            'join': action,
        }

    def manage_command(self, command: str, message: Dict[str, Any]) -> int:
        commands = self.get_commands()
        if command not in commands:
            return 1
        action = commands[command]
        self.send_reply(message, action)
        return 0

    def already_in_game_message(self) -> str:
        return 'You are already in a game. Type `quit` to leave.'

    def confirm_new_invitation(self, opponent: str) -> str:
        return 'You\'ve sent an invitation to play ' + self.game_name + ' with @**' +\
            self.get_user_by_email(opponent)['full_name'] + '**'

    def play_with_computer_help(self) -> str:
        if self.supports_computer:
            return '\n* To start a game with the computer, type\n`start game with` @**{}**'.format(self.get_bot_username())
        return ''

    def alert_new_invitation(self, game_id: str) -> str:
        # Since the first player invites, the challenger is always the first player
        player_email = self.get_players(game_id)[0]
        sender_name = self.get_username_by_email(player_email)
        return '**' + sender_name + ' has invited you to play a game of ' + self.game_name + '.**\n' +\
            self.get_formatted_game_object(game_id) + '\n\n' +\
            'Type ```accept``` to accept the game invitation\n' +\
            'Type ```decline``` to decline the game invitation.'

    def confirm_invitation_accepted(self, game_id: str) -> str:
        host = self.invites[game_id]['host']
        return 'Accepted invitation to play **{}** from @**{}**.'.format(self.game_name, self.get_username_by_email(host))

    def confirm_invitation_declined(self, game_id: str) -> str:
        host = self.invites[game_id]['host']
        return 'Declined invitation to play **{}** from @**{}**.'.format(self.game_name, self.get_username_by_email(host))

    def send_message(self, to: str, content: str, is_private: bool, subject: str = '') -> None:
        self.bot_handler.send_message(dict(
            type='private' if is_private else 'stream',
            to=to,
            content=content,
            subject=subject
        ))

    def send_reply(self, original_message: Dict[str, Any], content: str) -> None:
        self.bot_handler.send_reply(original_message, content)

    def usage(self) -> str:
        return '''
        Bot that allows users to play another user
        or the computer in a game of ''' + self.game_name + '''

        To see the entire list of commands, type
        @bot-name help
        '''

    def initialize(self, bot_handler: BotHandler) -> None:
        self.bot_handler = bot_handler
        self.get_user_cache()
        self.email = self.bot_handler.email
        self.full_name = self.bot_handler.full_name

    def handle_message(self, message: Dict[str, Any], bot_handler: BotHandler) -> None:
        try:
            self.bot_handler = bot_handler
            content = message['content'].strip()
            sender = message['sender_email'].lower()
            message['sender_email'] = message['sender_email'].lower()

            if self.email not in self.user_cache.keys() and self.supports_computer:
                self.add_user_to_cache({
                    'sender_email': self.email,
                    'sender_full_name': self.full_name
                })

            if sender == self.email:
                return

            if sender not in self.user_cache.keys():
                self.add_user_to_cache(message)
                logging.info('Added {} to user cache'.format(sender))

            if self.is_single_player:
                if content.lower().startswith('start game with') or content.lower().startswith('play game'):
                    self.send_reply(message, self.help_message_single_player())
                    return
                else:
                    val = self.manage_command(content.lower(), message)
                    if val == 0:
                        return

            if content.lower() == 'help' or content == '':
                if self.is_single_player:
                    self.send_reply(message, self.help_message_single_player())
                else:
                    self.send_reply(message, self.help_message())
                return

            elif content.lower() == 'rules':
                self.send_reply(message, self.rules)

            elif content.lower().startswith('start game with '):
                self.command_start_game_with(message, sender, content)

            elif content.lower() == 'start game':
                self.command_start_game(message, sender, content)

            elif content.lower().startswith('play game'):
                self.command_play(message, sender, content)

            elif content.lower() == 'accept':
                self.command_accept(message, sender, content)

            elif content.lower() == 'decline':
                self.command_decline(message, sender, content)

            elif content.lower() == 'quit':
                self.command_quit(message, sender, content)

            elif content.lower() == 'register':
                self.send_reply(
                    message, 'Hello @**{}**. Thanks for registering!'.format(message['sender_full_name']))

            elif content.lower() == 'leaderboard':
                self.command_leaderboard(message, sender, content)

            elif content.lower() == 'join':
                self.command_join(message, sender, content)

            elif self.is_user_in_game(sender) != '':
                self.parse_message(message)

            elif self.move_regex.match(content) is not None or content.lower() == 'draw' or content.lower() == 'forfeit':
                self.send_reply(
                    message, 'You are not in a game at the moment. Type `help` for help.')
            else:
                if self.is_single_player:
                    self.send_reply(message, self.help_message_single_player())
                else:
                    self.send_reply(message, self.help_message())
        except Exception as e:
            logging.exception(str(e))
            self.bot_handler.send_reply(message, 'Error {}.'.format(e))

    def is_user_in_game(self, user_email: str) -> str:
        for instance in self.instances.values():
            if user_email in instance.players:
                return instance.game_id
        return ''

    def command_start_game_with(self, message: Dict[str, Any], sender: str, content: str) -> None:
        if not self.is_user_not_player(sender, message):
            self.send_reply(
                message, self.already_in_game_message())
            return
        users = content.replace('start game with ', '').strip().split(', ')
        self.create_game_lobby(message, users)

    def command_start_game(self, message: Dict[str, Any], sender: str, content: str) -> None:
        if message['type'] == 'private':
            if self.is_single_player:
                self.send_reply(message, 'You are not allowed to play games in private messages.')
                return
            else:
                self.send_reply(
                    message, 'If you are starting a game in private messages, you must invite players. Type `help` for commands.')
        if not self.is_user_not_player(sender, message):
            self.send_reply(
                message, self.already_in_game_message())
            return
        self.create_game_lobby(message)
        if self.is_single_player:
            self.command_play(message, sender, content)

    def command_accept(self, message: Dict[str, Any], sender: str, content: str) -> None:
        if not self.is_user_not_player(sender, message):
            self.send_reply(
                message, self.already_in_game_message())
            return
        game_id = self.set_invite_by_user(sender, True, message)
        if game_id == '':
            self.send_reply(
                message, 'No active invites. Type `help` for commands.')
            return
        if message['type'] == 'private':
            self.send_reply(message, self.confirm_invitation_accepted(game_id))
        self.broadcast(
            game_id, '@**{}** has accepted the invitation.'.format(self.get_username_by_email(sender)))
        self.start_game_if_ready(game_id)

    def create_game_lobby(self, message: Dict[str, Any], users: List[str] = None) -> None:
        if users is None:
            users = []
        if self.is_game_in_subject(message['subject'], message['display_recipient']):
            self.send_reply(message, 'There is already a game in this stream.')
            return
        if len(users) > 0:
            users = self.verify_users(users, message=message)
            if len(users) + 1 < self.min_players:
                self.send_reply(
                    message, 'You must have at least {} players to play.\nGame cancelled.'.format(self.min_players))
                return
            if len(users) + 1 > self.max_players:
                self.send_reply(
                    message, 'The maximum number of players for this game is {}.'.format(self.max_players))
                return
        game_id = self.generate_game_id()
        stream_subject = '###private###'
        if message['type'] == 'stream':
            stream_subject = message['subject']
        self.invites[game_id] = {'host': message['sender_email'].lower(
        ), 'subject': stream_subject, 'stream': message['display_recipient']}
        if message['type'] == 'private':
            self.invites[game_id]['stream'] = 'games'
        for user in users:
            self.send_invite(game_id, user, message)
        if message['type'] == 'stream':
            if len(users) > 0:
                self.broadcast(game_id, 'If you were invited, and you\'re here, type "@**{}** accept" to accept the invite!'.format(
                    self.get_bot_username()), include_private=False)
            if len(users) + 1 < self.max_players:
                self.broadcast(
                    game_id, '**{}** wants to play **{}**. Type @**{}** join to play them!'.format(
                        self.get_username_by_email(message['sender_email']),
                        self.game_name,
                        self.get_bot_username())
                )
            if self.is_single_player:
                self.broadcast(game_id, '**{}** is now going to play {}!'.format(
                    self.get_username_by_email(message['sender_email']),
                    self.game_name)
                )

        if self.email in users:
            self.broadcast(game_id, 'Wait... That\'s me!',
                           include_private=True)
            if message['type'] == 'stream':
                self.broadcast(
                    game_id, '@**{}** accept'.format(self.get_bot_username()), include_private=False)
            game_id = self.set_invite_by_user(
                self.email, True, {'type': 'stream'})
            self.start_game_if_ready(game_id)

    def command_decline(self, message: Dict[str, Any], sender: str, content: str) -> None:
        if not self.is_user_not_player(sender, message):
            self.send_reply(
                message, self.already_in_game_message())
            return
        game_id = self.set_invite_by_user(sender, False, message)
        if game_id == '':
            self.send_reply(
                message, 'No active invites. Type `help` for commands.')
            return
        self.send_reply(message, self.confirm_invitation_declined(game_id))
        self.broadcast(
            game_id, '@**{}** has declined the invitation.'.format(self.get_username_by_email(sender)))
        if len(self.get_players(game_id, parameter='')) < self.min_players:
            self.cancel_game(game_id)

    def command_quit(self, message: Dict[str, Any], sender: str, content: str) -> None:
        game_id = self.get_game_id_by_email(sender)
        if message['type'] == 'private' and self.is_single_player:
            self.send_reply(message, 'You are not allowed to play games in private messages.')
            return
        if game_id == '':
            self.send_reply(
                message, 'You are not in a game. Type `help` for all commands.')
        sender_name = self.get_username_by_email(sender)
        self.cancel_game(game_id, reason='**{}** quit.'.format(sender_name))

    def command_join(self, message: Dict[str, Any], sender: str, content: str) -> None:
        if not self.is_user_not_player(sender, message):
            self.send_reply(
                message, self.already_in_game_message())
            return
        if message['type'] == 'private':
            self.send_reply(
                message, 'You cannot join games in private messages. Type `help` for all commands.')
            return
        game_id = self.get_invite_in_subject(
            message['subject'], message['display_recipient'])
        if game_id == '':
            self.send_reply(
                message, 'There is not a game in this subject. Type `help` for all commands.')
            return
        self.join_game(game_id, sender, message)

    def command_play(self, message: Dict[str, Any], sender: str, content: str) -> None:
        game_id = self.get_invite_in_subject(
            message['subject'], message['display_recipient'])
        if game_id == '':
            self.send_reply(
                message, 'There is not a game in this subject. Type `help` for all commands.')
            return
        num_players = len(self.get_players(game_id))
        if num_players >= self.min_players and num_players <= self.max_players:
            self.start_game(game_id)
        else:
            self.send_reply(
                message, 'Join {} more players to start the game'.format(self.max_players-num_players)
            )

    def command_leaderboard(self, message: Dict[str, Any], sender: str, content: str) -> None:
        stats = self.get_sorted_player_statistics()
        num = 5 if len(stats) > 5 else len(stats)
        top_stats = stats[0:num]
        response = '**Most wins**\n\n'
        raw_headers = ['games_won', 'games_drawn', 'games_lost', 'total_games']
        headers = ['Player'] + \
            [key.replace('_', ' ').title() for key in raw_headers]
        response += ' | '.join(headers)
        response += '\n' + ' | '.join([' --- ' for header in headers])
        for player, stat in top_stats:
            response += '\n **{}** | '.format(
                self.get_username_by_email(player))
            values = [str(stat[key]) for key in raw_headers]
            response += ' | '.join(values)
        self.send_reply(message, response)
        return

    def get_sorted_player_statistics(self) -> List[Tuple[str, Dict[str, int]]]:
        players = []
        for user_name, u in self.user_cache.items():
            if 'stats' in u.keys():
                players.append((user_name, u['stats']))
        return sorted(
            players,
            key=lambda player: (player[1]['games_won'],
                                player[1]['games_drawn'],
                                player[1]['total_games']),
            reverse=True
        )

    def send_invite(self, game_id: str, user_email: str, message: Dict[str, Any] = None) -> None:
        if message is None:
            message = {}
        self.invites[game_id].update({user_email.lower(): 'p'})
        self.send_message(user_email, self.alert_new_invitation(game_id), True)
        if message != {}:
            self.send_reply(message, self.confirm_new_invitation(user_email))

    def cancel_game(self, game_id: str, reason: str = '') -> None:
        if game_id in self.invites.keys():
            self.broadcast(game_id, 'Game cancelled.\n' + reason)
            del self.invites[game_id]
            return
        if game_id in self.instances.keys():
            self.instances[game_id].broadcast('Game ended.\n' + reason)
            del self.instances[game_id]
            return

    def start_game_if_ready(self, game_id: str) -> None:
        players = self.get_players(game_id)
        if len(players) == self.max_players:
            self.start_game(game_id)

    def start_game(self, game_id: str) -> None:
        players = self.get_players(game_id)
        subject = game_id
        stream = self.invites[game_id]['stream']
        if self.invites[game_id]['subject'] != '###private###':
            subject = self.invites[game_id]['subject']
        self.instances[game_id] = GameInstance(
            self, False, subject, game_id, players, stream)
        self.broadcast(game_id, 'The game has started in #{} {}'.format(
            stream, self.instances[game_id].subject) + '\n' + self.get_formatted_game_object(game_id))
        del self.invites[game_id]
        self.instances[game_id].start()

    def get_formatted_game_object(self, game_id: str) -> str:
        object = '''> **Game `{}`**
> {}
> {}/{} players'''.format(game_id, self.game_name, self.get_number_of_players(game_id), self.max_players)
        if game_id in self.instances.keys():
            instance = self.instances[game_id]
            if not self.is_single_player:
                object += '\n> **[Join Game](/#narrow/stream/{}/topic/{})**'.format(
                    instance.stream, instance.subject)
        return object

    def join_game(self, game_id: str, user_email: str, message: Dict[str, Any] = None) -> None:
        if message is None:
            message = {}
        if len(self.get_players(game_id)) >= self.max_players:
            if message != {}:
                self.send_reply(message, 'This game is full.')
            return
        self.invites[game_id].update({user_email: 'a'})
        self.broadcast(
            game_id, '@**{}** has joined the game'.format(self.get_username_by_email(user_email)))
        self.start_game_if_ready(game_id)

    def get_players(self, game_id: str, parameter: str = 'a') -> List[str]:
        if game_id in self.invites.keys():
            players = []  # type: List[str]
            if (self.invites[game_id]['subject'] == '###private###' and 'p' in parameter) or 'p' not in parameter:
                players = [self.invites[game_id]['host']]
            for player, accepted in self.invites[game_id].items():
                if player == 'host' or player == 'subject' or player == 'stream':
                    continue
                if parameter in accepted:
                    players.append(player)
            return players
        if game_id in self.instances.keys() and 'p' not in parameter:
            players = self.instances[game_id].players
            return players
        return []

    def get_game_info(self, game_id: str) -> Dict[str, Any]:
        game_info = {}  # type: Dict[str, Any]
        if game_id in self.instances.keys():
            instance = self.instances[game_id]
            game_info = {
                'game_id': game_id,
                'type': 'instance',
                'stream': instance.stream,
                'subject': instance.subject,
                'players': self.get_players(game_id)
            }
        if game_id in self.invites.keys():
            invite = self.invites[game_id]
            game_info = {
                'game_id': game_id,
                'type': 'invite',
                'stream': invite['stream'],
                'subject': invite['subject'],
                'players': self.get_players(game_id)
            }
        return game_info

    def get_user_by_name(self, name: str) -> Dict[str, Any]:
        name = name.strip()
        for user in self.user_cache.values():
            if 'full_name' in user.keys():
                if user['full_name'].lower() == name.lower():
                    return user
        return {}

    def get_number_of_players(self, game_id: str) -> int:
        num = len(self.get_players(game_id))
        return num

    def parse_message(self, message: Dict[str, Any]) -> None:
        game_id = self.is_user_in_game(message['sender_email'])
        game = self.get_game_info(game_id)
        if message['type'] == 'private':
            if self.is_single_player:
                self.send_reply(message, self.help_message_single_player())
                return
            self.send_reply(message, 'Join your game using the link below!\n\n{}'.format(
                self.get_formatted_game_object(game_id)))
            return
        if game['subject'] != message['subject'] or game['stream'] != message['display_recipient']:
            if game_id not in self.pending_subject_changes:
                self.send_reply(message, 'Your current game is not in this subject. \n\
To move subjects, send your message again, otherwise join the game using the link below.\n\n\
{}'.format(self.get_formatted_game_object(game_id)))
                self.pending_subject_changes.append(game_id)
                return
            self.pending_subject_changes.remove(game_id)
            self.change_game_subject(
                game_id, message['display_recipient'], message['subject'], message)
        self.instances[game_id].handle_message(
            message['content'], message['sender_email'])

    def change_game_subject(
        self,
        game_id: str,
        stream_name: str,
        subject_name: str,
        message: Dict[str, Any] = None
    ) -> None:
        if message is None:
            message = {}
        if self.get_game_instance_by_subject(stream_name, subject_name) is not None:
            if message != {}:
                self.send_reply(
                    message, 'There is already a game in this subject.')
            return
        if game_id in self.instances.keys():
            self.instances[game_id].change_subject(stream_name, subject_name)
        if game_id in self.invites.keys():
            invite = self.invites[game_id]
            invite['stream'] = stream_name
            invite['subject'] = stream_name

    def set_invite_by_user(self, user_email: str, is_accepted: bool, message: Dict[str, Any]) -> str:
        user_email = user_email.lower()
        for game, users in self.invites.items():
            if user_email in users.keys():
                if is_accepted:
                    if message['type'] == 'private':
                        users[user_email] = 'pa'
                    else:
                        users[user_email] = 'a'
                else:
                    users.pop(user_email)
                return game
        return ''

    def add_user_to_cache(self, message: Dict[str, Any]) -> None:
        user = {
            'email': message['sender_email'].lower(),
            'full_name': message['sender_full_name'],
            'stats': {
                'total_games': 0,
                'games_won': 0,
                'games_lost': 0,
                'games_drawn': 0
            }
        }
        self.user_cache.update({message['sender_email'].lower(): user})
        self.put_user_cache()

    def put_user_cache(self) -> Dict[str, Any]:
        user_cache_str = json.dumps(self.user_cache)
        self.bot_handler.storage.put('users', user_cache_str)
        return self.user_cache

    def get_user_cache(self) -> Dict[str, Any]:
        try:
            user_cache_str = self.bot_handler.storage.get('users')
        except KeyError:
            return {}
        self.user_cache = json.loads(user_cache_str)
        return self.user_cache

    def verify_users(self, users: List[str], message: Dict[str, Any] = None) -> List[str]:
        if message is None:
            message = {}
        verified_users = []
        failed = False
        for u in users:
            user = u.strip().lstrip('@**').rstrip('**')
            if (user == self.get_bot_username() or user == self.email) and not self.supports_computer:
                self.send_reply(
                    message, 'You cannot play against the computer in this game.')
            if '@' not in user:
                user_obj = self.get_user_by_name(user)
                if user_obj == {}:
                    self.send_reply(
                        message, 'I don\'t know {}. Tell them to say @**{}** register'.format(u, self.get_bot_username()))
                    failed = True
                    continue
                user = user_obj['email']
            if self.is_user_not_player(user, message):
                verified_users.append(user)
            else:
                failed = True
        if failed:
            return []
        else:
            return verified_users

    def get_game_instance_by_subject(self, subject_name: str, stream_name: str) -> Any:
        for instance in self.instances.values():
            if instance.subject == subject_name and instance.stream == stream_name:
                return instance
        return None

    def get_invite_in_subject(self, subject_name: str, stream_name: str) -> str:
        for key, invite in self.invites.items():
            if invite['subject'] == subject_name and invite['stream'] == stream_name:
                return key
        return ''

    def is_game_in_subject(self, subject_name: str, stream_name: str) -> bool:
        return self.get_invite_in_subject(subject_name, stream_name) != '' or \
            self.get_game_instance_by_subject(
                subject_name, stream_name) is not None

    def is_user_not_player(self, user_email: str, message: Dict[str, Any] = None) -> bool:
        if message is None:
            message = {}
        user = self.get_user_by_email(user_email)
        if user == {}:
            if message != {}:
                self.send_reply(message, 'I don\'t know {}. Tell them to use @**{}** register'.format(
                    user_email, self.get_bot_username()))
            return False
        for instance in self.instances.values():
            if user_email in instance.players:
                return False
        for invite in self.invites.values():
            for u in invite.keys():
                if u == 'host':
                    if user_email == invite['host']:
                        return False
                if u == user_email and 'a' in invite[u]:
                    return False
        return True

    def generate_game_id(self) -> str:
        id = ''
        valid_characters = 'abcdefghijklmnopqrstuvwxyz0123456789'
        for i in range(6):
            id += valid_characters[random.randrange(0, len(valid_characters))]
        return id

    def broadcast(self, game_id: str, content: str, include_private: bool = True) -> bool:
        if include_private:
            private_recipients = self.get_players(game_id, parameter='p')
            if private_recipients is not None:
                for user in private_recipients:
                    self.send_message(user, content, True)
        if game_id in self.invites.keys():
            if self.invites[game_id]['subject'] != '###private###':
                self.send_message(
                    self.invites[game_id]['stream'], content, False, self.invites[game_id]['subject'])
                return True
        if game_id in self.instances.keys():
            self.send_message(
                self.instances[game_id].stream, content, False, self.instances[game_id].subject)
            return True
        return False

    def get_username_by_email(self, user_email: str) -> str:
        return self.get_user_by_email(user_email)['full_name']

    def get_user_by_email(self, user_email: str) -> Dict[str, Any]:
        if user_email in self.user_cache:
            return self.user_cache[user_email]
        return {}

    def get_game_id_by_email(self, user_email: str) -> str:
        for instance in self.instances.values():
            if user_email in instance.players:
                return instance.game_id
        for game_id in self.invites:
            players = self.get_players(game_id)
            if user_email in players:
                return game_id
        return ''

    def get_bot_username(self) -> str:
        return self.bot_handler.full_name


class GameInstance:
    '''
    The GameInstance class handles the game logic for a certain game,
    and is associated with a certain stream.

    It gets player info from GameAdapter

    It only runs when the game is being played, not in the invite
    or waiting states.
    '''

    def __init__(self, gameAdapter: GameAdapter, is_private: bool, subject: str, game_id: str, players: List[str], stream: str) -> None:
        self.gameAdapter = gameAdapter
        self.is_private = is_private
        self.subject = subject
        self.game_id = game_id
        self.players = players
        self.stream = stream
        self.model = deepcopy(self.gameAdapter.model())
        self.board = self.model.current_board
        self.turn = random.randrange(0, len(players)) - 1
        self.current_draw = {}  # type: Dict[str, bool]
        self.current_messages = []  # type: List[str]
        self.is_changing_subject = False

    def start(self) -> None:
        self.current_messages.append(self.get_start_message())
        self.current_messages.append(self.parse_current_board())
        self.next_turn()

    def change_subject(self, stream: str, subject: str) -> None:
        self.stream = stream
        self.subject = subject
        self.current_messages.append(self.parse_current_board())
        self.broadcast_current_message()

    def get_player_text(self) -> str:
        player_text = ''
        for player in self.players:
            player_text += ' @**{}**'.format(
                self.gameAdapter.get_username_by_email(player))
        return player_text

    def get_start_message(self) -> str:
        start_message = 'Game `{}` started.\n*Remember to start your message with* @**{}**'.format(
            self.game_id, self.gameAdapter.get_bot_username())
        if not self.is_private:
            player_text = '\n**Players**'
            player_text += self.get_player_text()
            start_message += player_text
        start_message += '\n' + self.gameAdapter.gameMessageHandler.game_start_message()
        return start_message

    def handle_message(self, content: str, player_email: str) -> None:
        if content == 'forfeit':
            player_name = self.gameAdapter.get_username_by_email(player_email)
            self.broadcast('**{}** forfeited!'.format(player_name))
            self.end_game('except:' + player_email)
            return
        if content == 'draw':
            if player_email in self.current_draw.keys():
                self.current_draw[player_email] = True
            else:
                self.current_draw = {p: False for p in self.players}
                self.broadcast('**{}** has voted for a draw!\nType `draw` to accept'.format(
                    self.gameAdapter.get_username_by_email(player_email)))
                self.current_draw[player_email] = True
            if self.check_draw():
                self.end_game('draw')
            return
        if self.is_turn_of(player_email):
            self.handle_current_player_command(content)
        else:
            if self.gameAdapter.is_single_player:
                self.broadcast('It\'s your turn')
            else:
                self.broadcast('It\'s **{}**\'s ({}) turn.'.format(
                    self.gameAdapter.get_username_by_email(
                        self.players[self.turn]),
                    self.gameAdapter.gameMessageHandler.get_player_color(self.turn)))

    def broadcast(self, content: str) -> None:
        self.gameAdapter.broadcast(self.game_id, content)

    def check_draw(self) -> bool:
        for d in self.current_draw.values():
            if not d:
                return False
        return len(self.current_draw.values()) > 0

    def handle_current_player_command(self, content: str) -> None:
        re_result = self.gameAdapter.move_regex.match(content)
        if re_result is None:
            self.broadcast(self.gameAdapter.move_help_message)
            return
        self.make_move(content, False)

    def make_move(self, content: str, is_computer: bool) -> None:
        try:
            self.model.make_move(content, self.turn, is_computer)
        # Keep the turn of the same player
        except SamePlayerMove as smp:
            self.same_player_turn(content, smp.message, is_computer)
            return
        except BadMoveException as e:
            self.broadcast(e.message)
            self.broadcast(self.parse_current_board())
            return
        if not is_computer:
            self.current_messages.append(self.gameAdapter.gameMessageHandler.alert_move_message(
                '**{}**'.format(self.gameAdapter.get_username_by_email(self.players[self.turn])), content))
        self.current_messages.append(self.parse_current_board())
        game_over = self.model.determine_game_over(self.players)
        if game_over:
            self.broadcast_current_message()
            if game_over == 'current turn':
                game_over = self.players[self.turn]
            self.end_game(game_over)
            return
        self.next_turn()

    def is_turn_of(self, player_email: str) -> bool:
        return self.players[self.turn].lower() == player_email.lower()

    def same_player_turn(self, content: str, message: str, is_computer: bool) -> None:
        if not is_computer:
            self.current_messages.append(self.gameAdapter.gameMessageHandler.alert_move_message(
                '**{}**'.format(self.gameAdapter.get_username_by_email(self.players[self.turn])), content))
        self.current_messages.append(self.parse_current_board())
        # append custom message the game wants to give for the next move
        self.current_messages.append(message)
        game_over = self.model.determine_game_over(self.players)
        if game_over:
            self.broadcast_current_message()
            if game_over == 'current turn':
                game_over = self.players[self.turn]
            self.end_game(game_over)
            return
        self.current_messages.append('It\'s **{}**\'s ({}) turn.'.format(
            self.gameAdapter.get_username_by_email(self.players[self.turn]),
            self.gameAdapter.gameMessageHandler.get_player_color(self.turn)
        ))
        self.broadcast_current_message()
        if self.players[self.turn] == self.gameAdapter.email:
            self.make_move('', True)

    def next_turn(self) -> None:
        self.turn += 1
        if self.turn >= len(self.players):
            self.turn = 0
        if self.gameAdapter.is_single_player:
            self.current_messages.append('It\'s your turn.')
        else:
            self.current_messages.append('It\'s **{}**\'s ({}) turn.'.format(
                self.gameAdapter.get_username_by_email(self.players[self.turn]),
                self.gameAdapter.gameMessageHandler.get_player_color(self.turn)
            ))
        self.broadcast_current_message()
        if self.players[self.turn] == self.gameAdapter.email:
            self.make_move('', True)

    def broadcast_current_message(self) -> None:
        content = '\n\n'.join(self.current_messages)
        self.broadcast(content)
        self.current_messages = []

    def parse_current_board(self) -> Any:
        return self.gameAdapter.gameMessageHandler.parse_board(self.model.current_board)

    def end_game(self, winner: str) -> None:
        loser = ''
        if winner == 'draw':
            self.broadcast('It was a draw!')
        elif winner.startswith('except:'):
            loser = winner.lstrip('except:')
        else:
            winner_name = self.gameAdapter.get_username_by_email(winner)
            self.broadcast('**{}** won! :tada:'.format(winner_name))
        for u in self.players:
            values = {'total_games': 1, 'games_won': 0,
                      'games_lost': 0, 'games_drawn': 0}
            if loser == '':
                if u == winner:
                    values.update({'games_won': 1})
                elif winner == 'draw':
                    values.update({'games_drawn': 1})
                else:
                    values.update({'games_lost': 1})
            else:
                if u == loser:
                    values.update({'games_lost': 1})
                else:
                    values.update({'games_won': 1})
            self.gameAdapter.add_user_statistics(u, values)
        if self.gameAdapter.email in self.players:
            self.send_win_responses(winner)
        self.gameAdapter.cancel_game(self.game_id)

    def send_win_responses(self, winner: str) -> None:
        if winner == self.gameAdapter.email:
            self.broadcast('I won! Well Played!')
        elif winner == 'draw':
            self.broadcast('It was a draw! Well Played!')
        else:
            self.broadcast('You won! Nice!')
