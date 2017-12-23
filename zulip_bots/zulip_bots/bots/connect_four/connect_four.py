# @TODO: place bot owner name in config file, allow bot owner to run special commands

import re
from copy import deepcopy
from zulip_bots.bots.connect_four.controller import ConnectFourModel

class InputVerification(object):
    verified_users = []

    all_valid_commands = ['help', 'status', 'start game with computer', 'start game with \w+@\w+\.\w+',
                          'withdraw invitation', 'accept', 'decline', 'move \d$', 'quit', 'confirm quit']

    # Every command that can be run, in states requiring user verification, by each player
    verified_commands = {
        'waiting': ['start game with computer', 'start game with \w+@\w+\.\w+'],
        'inviting': [['withdraw invitation'], ['accept', 'decline']],
        'playing': [['move \d$', 'quit', 'confirm quit'], ['quit', 'confirm quit']]
    }

    def permission_lacking_message(self, command):
        return 'Sorry, but you can\'t run the command ```' + command + '```'

    def update_commands(self, turn):
        self.verified_commands['playing'][-1 * turn + 1].remove('move \d$')
        self.verified_commands['playing'][turn].append('move \d$')

    def reset_commands(self):
        self.verified_commands['playing'] = [['move \d$', 'quit', 'confirm quit'], ['quit', 'confirm quit']]

    def regex_match_in_array(self, command_array, command):
        for command_regex in command_array:
            if re.compile(command_regex).match(command.lower()):
                return True

        return False

    def valid_command(self, command):
        return self.regex_match_in_array(self.all_valid_commands, command)

    def verify_user(self, user):
        return user in self.verified_users

    def verify_command(self, user, command, state):
        if state != 'waiting':
            command_array = self.verified_commands[state][self.verified_users.index(user)]
        else:
            command_array = self.verified_commands[state]

        return self.regex_match_in_array(command_array, command)

class StateManager(object):
    def __init__(self, main_bot_handler):
        self.users = None
        self.state = ''
        self.user_messages = []
        self.opponent_messages = []
        self.main_bot_handler = main_bot_handler

    # Updates to the main bot handler that all state managers must use
    def basic_updates(self):
        if self.users is not None:
            self.main_bot_handler.inputVerification.verified_users = self.users

        if self.state:
            self.main_bot_handler.state = self.state

        self.main_bot_handler.user_messages = self.user_messages

        self.main_bot_handler.opponent_messages = self.opponent_messages

    def reset_self(self):
        self.users = None
        self.user_messages = []
        self.opponent_messages = []
        self.state = ''

class GameCreator(StateManager):
    def __init__(self, main_bot_handler):
        super(GameCreator, self).__init__(main_bot_handler)
        self.gameHandler = None
        self.invitationHandler = None

    def handle_message(self, content, sender):
        if content == 'start game with computer':
            self.users = [sender]
            self.state = 'playing'
            self.gameHandler = GameHandler(self.main_bot_handler, 'one_player')

            self.user_messages.append('**You started a new game with the computer!**')
            self.user_messages.append(self.gameHandler.parse_board())
            self.user_messages.append(self.gameHandler.your_turn_message())

        elif re.compile('\w+@\w+\.\w+').search(content):
            opponent = re.compile('(\w+@\w+\.\w+)').search(content).group(1)

            if opponent == sender:
                self.user_messages.append('You can\'t play against yourself!')
                self.update_main_bot_handler()
                return

            self.users = [sender, opponent]
            self.state = 'inviting'
            self.gameHandler = GameHandler(self.main_bot_handler, 'two_player')
            self.invitationHandler = InvitationHandler(self.main_bot_handler)

            self.user_messages.append(self.invitationHandler.confirm_new_invitation(opponent))

            self.opponent_messages.append(self.invitationHandler.alert_new_invitation(sender))

        self.update_main_bot_handler()

    def update_main_bot_handler(self):
        self.basic_updates()

        self.main_bot_handler.player_cache = self.users

        self.main_bot_handler.gameHandler = deepcopy(self.gameHandler)

        if self.invitationHandler:
            self.main_bot_handler.invitationHandler = deepcopy(self.invitationHandler)

        self.reset_self()

class GameHandler(StateManager):
    def __init__(self, main_bot_handler, game_type, board = ConnectFourModel().blank_board, turn = 0):
        super(GameHandler, self).__init__(main_bot_handler)
        self.game_type = game_type
        self.board = board
        self.turn = turn
        self.game_ended = False
        self.connectFourModel = ConnectFourModel()
        self.connectFourModel.update_board(board)
        self.tokens = [':blue_circle:', ':red_circle:']

    def parse_board(self):
        # Header for the top of the board
        board_str = ':one: :two: :three: :four: :five: :six: :seven:'

        for row in range(0, 6):
            board_str += '\n\n'
            for column in range(0, 7):
                if self.board[row][column] == 0:
                    board_str += ':heavy_large_circle: '
                elif self.board[row][column] == 1:
                    board_str += ':blue_circle: '
                elif self.board[row][column] == -1:
                    board_str += ':red_circle: '

        return board_str

    def your_turn_message(self):
        return '**It\'s your move!**\n' +\
               'type ```move <column-number>``` to make your move\n\n' +\
               'You are ' + self.tokens[self.turn]

    def wait_turn_message(self, opponent):
        return 'Waiting for ' + opponent + ' to move'

    def alert_move_message(self, original_player, column_number):
        return '**' + original_player + ' moved in column ' + str(column_number + 1) + '**.'

    def append_game_over_messages(self, result):
        if result == 'draw':
            self.user_messages.append('**It\'s a draw!**')
            self.opponent_messages.append('**It\'s a draw!**')
        else:
            if result != 'the Computer':
                self.user_messages.append('**Congratulations, you win! :tada:**')
                self.opponent_messages.append('Sorry, but ' + result + ' won :cry:')
            else:
                self.user_messages.append('Sorry, but ' + result + ' won :cry:')

    def get_player_token(self, sender):
        player = self.main_bot_handler.inputVerification.verified_users.index(sender)
        # This computation will return 1 for player 0, and -1 for player 1, as is expected
        return (-2) * player + 1

    def toggle_turn(self):
        self.turn = (-1) * self.turn + 1

    def end_game(self):
        self.state = 'waiting'
        self.game_ended = True
        self.users = []

    def handle_move(self, column_number, token_number, player_one, player_two, computer_play = False):
        if not self.connectFourModel.validate_move(column_number):
            self.user_messages.append('That\'s an invalid move. Please specify a column' +
                                      ' with at least one blank space, between 1 and 7')
            return

        self.board = self.connectFourModel.make_move(column_number, token_number)

        if not computer_play:
            self.user_messages.append('You placed your token in column ' + str(column_number + 1) + '.')
            self.user_messages.append(self.parse_board())

            self.opponent_messages.append(self.alert_move_message(self.sender, column_number))
            self.opponent_messages.append(self.parse_board())

        else:
            self.user_messages.append(self.alert_move_message('the Computer', column_number))
            self.user_messages.append(self.parse_board())

        game_over = self.connectFourModel.determine_game_over(player_one, player_two)

        if game_over:
            self.append_game_over_messages(game_over)
            self.end_game()

        else:
            self.toggle_turn()

            self.main_bot_handler.inputVerification.update_commands(self.turn)

            if not computer_play:
                self.user_messages.append(self.wait_turn_message(self.opponent))

                self.opponent_messages.append(self.your_turn_message())

            else:
                self.user_messages.append(self.your_turn_message())

    def handle_message(self, content, sender):
        self.sender = sender

        if self.game_type == 'two_player':
            opponent_array = deepcopy(self.main_bot_handler.inputVerification.verified_users)
            opponent_array.remove(sender)
            self.opponent = opponent_array[0]
        else:
            self.opponent = 'the Computer'

        if content == 'quit':
            self.user_messages.append('Are you sure you want to quit? You will forfeit the game!\n' +
                                      'Type ```confirm quit``` to forfeit.')

        elif content == 'confirm quit':
            self.end_game()

            self.user_messages.append('**You have forfeit the game**\nSorry, but you lost :cry:')

            self.opponent_messages.append('**' + sender + ' has forfeit the game**\nCongratulations, you win! :tada:')

        elif re.compile('move \d$').match(content):
            player_one = player_one = self.main_bot_handler.inputVerification.verified_users[0]
            player_two = 'the Computer' if self.game_type == 'one_player' else self.main_bot_handler.inputVerification.verified_users[1]

            human_move = int(re.compile('move (\d)$').search(content).group(1)) - 1
            human_token_number = self.get_player_token(sender)

            self.handle_move(human_move, human_token_number, player_one, player_two)

            if not self.game_ended and self.game_type == 'one_player':
                computer_move = self.connectFourModel.computer_move()
                computer_token_number = -1

                self.handle_move(computer_move, computer_token_number, player_one, player_two, computer_play = True)

        self.update_main_bot_handler()

    def update_main_bot_handler(self):
        if self.game_type == 'one_player':
            self.opponent_messages = []

        self.basic_updates()

        if self.game_ended:
            self.main_bot_handler.gameHandler = None

        self.reset_self()

class InvitationHandler(StateManager):
    def __init__(self, main_bot_handler):
        super(InvitationHandler, self).__init__(main_bot_handler)
        self.game_cancelled = False
        self.gameHandler = object

    def confirm_new_invitation(self, opponent):
        return 'You\'ve sent an invitation to play Connect Four with ' +\
            opponent + '. I\'ll let you know when they respond to the invitation'

    def alert_new_invitation(self, challenger):
        # Since the first player invites, the challenger is always the first player
        return '**' + challenger + ' has invited you to play a game of Connect Four.**\n' +\
            'Type ```accept``` to accept the game invitation\n' +\
            'Type ```decline``` to decline the game invitation.'

    def handle_message(self, content, sender):
        challenger = self.main_bot_handler.inputVerification.verified_users[0]
        opponent = self.main_bot_handler.inputVerification.verified_users[1]

        if content.lower() == 'accept':
            self.state = 'playing'

            self.user_messages.append('You accepted the invitation to play with ' + challenger)
            self.user_messages.append(self.main_bot_handler.gameHandler.wait_turn_message(challenger))

            self.opponent_messages.append('**' + opponent + ' has accepted your invitation to play**')
            self.opponent_messages.append(self.main_bot_handler.gameHandler.parse_board())
            self.opponent_messages.append(self.main_bot_handler.gameHandler.your_turn_message())

        elif content.lower() == 'decline':
            self.state = 'waiting'
            self.users = []
            self.gameHandler = None

            self.user_messages.append('You declined the invitation to play with ' + challenger)

            self.opponent_messages.append('**' + opponent + ' has declined your invitation to play**\n' +
                                          'Invite another player by typing ```start game with user@example.com```')

        elif content.lower() == 'withdraw invitation':
            self.state = 'waiting'
            self.users = []
            self.gameHandler = None

            self.user_messages.append('Your invitation to play ' + opponent + ' has been withdrawn')

            self.opponent_messages.append('**' + challenger + ' has withdrawn his invitation to play you**\n' +
                                          'Type ``` start game with ' + challenger + '``` if you would like to play them.')

        self.update_main_bot_handler()

    def update_main_bot_handler(self):
        self.basic_updates()

        self.main_bot_handler.invitationHandler = None

        if self.gameHandler is None:
            self.main_bot_handler.gameHandler = self.gameHandler

        self.reset_self()

class ConnectFourBotHandler(object):
    '''
    Bot that allows users to player another user
    or the computer in a game of Connect Four
    '''

    def get_stored_data(self):
        # return self.data # Uncomment and rerun bot to reset data if users are abusing the bot
        return self.bot_handler.storage.get('connect_four')

    def update_data(self):
        self.state = self.data['state']

        if 'users' in self.data:
            self.inputVerification.verified_users = self.data['users']

        if self.state == 'inviting':
            self.invitationHandler = InvitationHandler(self)
            self.gameHandler = GameHandler(self, self.data['game_type'])

        elif self.state == 'playing':
            self.gameHandler = GameHandler(self, self.data['game_type'], board = self.data['board'], turn = self.data['turn'])

    def put_stored_data(self):
        self.data = {}

        self.data['state'] = self.state

        if self.inputVerification.verified_users:
            self.data['users'] = self.inputVerification.verified_users

        if self.state == 'inviting':
            self.data['game_type'] = self.gameHandler.game_type

        elif self.state == 'playing':
            self.data['game_type'] = self.gameHandler.game_type
            self.data['board'] = self.gameHandler.board
            self.data['turn'] = self.gameHandler.turn

        self.bot_handler.storage.put('connect_four', self.data)

    # Stores the current state of the game. Either 'waiting 'inviting' or 'playing'
    state = 'waiting'

    # Stores the users, in case one of the state managers modifies the verified users
    player_cache = []

    # Object-wide storage to the bot_handler to allow custom message-sending function
    bot_handler = None

    inputVerification = InputVerification()
    invitationHandler = None
    gameHandler = None
    gameCreator = None

    user_messages = []
    opponent_messages = []

    # Stores a compact version of all data the bot is managing
    data = {'state': 'waiting'}

    def status_message(self):
        prefix = '**Connect Four Game Status**\n' +\
            '*If you suspect users are abusing the bot,' +\
            ' please alert the bot owner*\n\n'

        if self.state == 'playing':
            if self.gameHandler.game_type == 'one_player':
                message = 'The bot is currently running a single player game' +\
                          ' for ' + self.inputVerification.verified_users[0] + '.'

            elif self.gameHandler.game_type == 'two_player':
                message = 'The bot is currently running a two player game ' +\
                          'between ' + self.inputVerification.verified_users[0] +\
                          ' and ' + self.inputVerification.verified_users[1] + '.'

        elif self.state == 'inviting':
            message = self.inputVerification.verified_users[0] + '\'s' +\
                ' invitation to play ' + self.inputVerification.verified_users[1] +\
                ' is still pending. Wait for the game to finish to play a game.'

        elif self.state == 'waiting':
            message = '**The bot is not running a game right now!**\n' + \
                'Type ```start game with user@example.com``` '  +\
                'to start a game with another user,\n' +\
                'or type ```start game with computer``` ' +\
                'to start a game with the computer'

        return prefix + message

    def help_message(self):
        return '**Connect Four Bot Help:**\n' + \
            '*Preface all commands with @bot-name*\n\n' + \
            '* To see the current status of the game, type\n' + \
            '```status```\n' + \
            '* To start a game against the computer, type\n' + \
            '```start game with computer```\n' +\
            '* To start a game against another player, type\n' + \
            '```start game with user@example.com```\n' + \
            '* To make your move during a game, type\n' + \
            '```move <column-number>```\n' + \
            '* To quit a game at any time, type\n' + \
            '```quit```\n' + \
            '* To withdraw an invitation, type\n' + \
            '```cancel game```'

    def send_message(self, user, content):
        self.bot_handler.send_message(dict(
            type = 'private',
            to = user,
            content = content
        ))

    # Sends messages returned from helper classes, where user, is the user who sent the bot the original messages
    def send_message_arrays(self, user):
        if self.opponent_messages:
            opponent_array = deepcopy(self.player_cache)
            opponent_array.remove(user)
            opponent = opponent_array[0]

        for message in self.user_messages:
            self.send_message(user, message)

        for message in self.opponent_messages:
            self.send_message(opponent, message)

        self.user_messages = []
        self.opponent_messages = []

    def parse_message(self, message):
        content = message['content'].strip()
        sender = message['sender_email']
        return (content, sender)

    def usage(self):
        return '''
        Bot that allows users to play another user
        or the computer in a game of Connect Four.

        To see the entire list of commands, type
        @bot-name help
        '''

    def initialize(self, bot_handler):
        self.gameCreator = GameCreator(self)
        self.inputVerification.reset_commands()
        if not bot_handler.storage.contains('connect_four'):
            bot_handler.storage.put('connect_four', self.data)

    def handle_message(self, message, bot_handler):
        self.bot_handler = bot_handler

        self.data = self.get_stored_data()
        self.update_data()

        self.player_cache = self.inputVerification.verified_users
        content, sender = self.parse_message(message)

        if not self.inputVerification.valid_command(content.lower()):
            self.send_message(sender, 'Sorry, but I couldn\'t understand your input.\n'
                                      'Type ```help``` to see a full list of commands.')
            return

        # Messages that can be sent regardless of state or user
        elif content.lower() == 'help' or content == '':
            self.send_message(sender, self.help_message())
            return

        elif content.lower() == 'status':
            self.send_message(sender, self.status_message())
            return

        elif self.state == 'waiting':
            if not self.inputVerification.verify_command(sender, content.lower(), 'waiting'):
                self.send_message(sender, self.inputVerification.permission_lacking_message(content))

            self.gameCreator.handle_message(content, sender)

        elif not self.inputVerification.verify_user(sender):
            self.send_message(sender, 'Sorry, but other users are already using the bot.'
                                      'Type ```status``` to see the current status of the bot.')
            return

        elif self.state == 'inviting':
            if not self.inputVerification.verify_command(sender, content.lower(), 'inviting'):
                self.send_message(sender, self.inputVerification.permission_lacking_message(content))
                return

            self.invitationHandler.handle_message(content, sender)

        elif self.state == 'playing':
            if not self.inputVerification.verify_command(sender, content.lower(), 'playing'):
                self.send_message(sender, self.inputVerification.permission_lacking_message(content))
                return

            self.gameHandler.handle_message(content, sender)

        self.send_message_arrays(sender)
        self.put_stored_data()

handler_class = ConnectFourBotHandler
