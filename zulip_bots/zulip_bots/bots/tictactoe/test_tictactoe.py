from zulip_bots.test_lib import BotTestCase

from unittest.mock import patch

class TestTictactoeBot(BotTestCase):
    bot_name = 'tictactoe'

    def test_bot(self):
        messages = [  # Template for message inputs to test, absent of message content
            {
                'type': 'stream',
                'display_recipient': 'some stream',
                'subject': 'some subject',
                'sender_email': 'foo_sender@zulip.com',
            },
            {
                'type': 'private',
                'sender_email': 'foo_sender@zulip.com',
            },
        ]
        private_response = {
            'type': 'private',
            'to': 'foo_sender@zulip.com',
            'subject': 'foo_sender@zulip.com',  # FIXME Requiring this in bot is a bug?
        }

        msg = dict(
            help = "*Help for Tic-Tac-Toe bot* \nThe bot responds to messages starting with @mention-bot.\n**@mention-bot new** will start a new game (but not if you're already in the middle of a game). You must type this first to start playing!\n**@mention-bot help** will return this help function.\n**@mention-bot quit** will quit from the current game.\n**@mention-bot <coordinate>** will make a move at the given coordinate.\nCoordinates are entered in a (row, column) format. Numbering is from top to bottom and left to right. \nHere are the coordinates of each position. (Parentheses and spaces are optional). \n(1, 1)  (1, 2)  (1, 3) \n(2, 1)  (2, 2)  (2, 3) \n(3, 1) (3, 2) (3, 3) \n",
            didnt_understand = "Hmm, I didn't understand your input. Type **@tictactoe help** or **@ttt help** to see valid inputs.",
            new_game = "Welcome to tic-tac-toe! You'll be x's and I'll be o's. Your move first!\nCoordinates are entered in a (row, column) format. Numbering is from top to bottom and left to right.\nHere are the coordinates of each position. (Parentheses and spaces are optional.) \n(1, 1)  (1, 2)  (1, 3) \n(2, 1)  (2, 2)  (2, 3) \n(3, 1) (3, 2) (3, 3) \n Your move would be one of these. To make a move, type @mention-bot followed by a space and the coordinate.",
            already_playing = "You're already playing a game! Type **@tictactoe help** or **@ttt help** to see valid inputs.",
            already_played_there = 'That space is already filled, sorry!',
            successful_quit = "You've successfully quit the game.",
            after_1_1 = ("[ x _ _ ]\n[ _ _ _ ]\n[ _ _ _ ]\n"
                         "My turn:\n[ x _ _ ]\n[ _ o _ ]\n[ _ _ _ ]\n"
                         "Your turn! Enter a coordinate or type help."),
            after_2_1 = ("[ x _ _ ]\n[ x o _ ]\n[ _ _ _ ]\n"
                         "My turn:\n[ x _ _ ]\n[ x o _ ]\n[ o _ _ ]\n"
                         "Your turn! Enter a coordinate or type help."),
            after_1_3 = ("[ x _ x ]\n[ x o _ ]\n[ o _ _ ]\n"
                         "My turn:\n[ x o x ]\n[ x o _ ]\n[ o _ _ ]\n"
                         "Your turn! Enter a coordinate or type help."),
            after_3_2 = ("[ x o x ]\n[ x o _ ]\n[ o x _ ]\n"
                         "My turn:\n[ x o x ]\n[ x o _ ]\n[ o x o ]\n"
                         "Your turn! Enter a coordinate or type help."),
            after_2_3_draw = ("[ x o x ]\n[ x o x ]\n[ o x o ]\n"
                              "It's a draw! Neither of us was able to win."),
            after_2_3_try_lose = ("[ x _ _ ]\n[ _ o x ]\n[ _ _ _ ]\n"
                                  "My turn:\n[ x _ _ ]\n[ _ o x ]\n[ _ o _ ]\n"
                                  "Your turn! Enter a coordinate or type help."),
            after_2_1_lost = ("[ x _ _ ]\n[ x o x ]\n[ _ o _ ]\n"
                              "My turn:\n[ x o _ ]\n[ x o x ]\n[ _ o _ ]\n"
                              "Game over! I've won!"),
        )

        conversation = [
            # Empty message
            ("", msg['didnt_understand']),
            # Non-command
            ("adboh", msg['didnt_understand']),
            # Help command
            ("help", msg['help']),
            # Command: quit not understood with no game
            ("quit", msg['didnt_understand']),
            # Can quit if new game and have state
            ("new", msg['new_game']),
            ("quit", msg['successful_quit']),
            # Quit not understood when no game FIXME improve response?
            ("quit", msg['didnt_understand']),
            # New right after new just restarts
            ("new", msg['new_game']),
            ("new", msg['new_game']),
            # Make a corner play
            ("(1,1)", msg['after_1_1']),
            # New while playing doesn't just restart
            ("new", msg['already_playing']),
            # User played in this location already
            ("(1,1)", msg['already_played_there']),
            # ... and bot played here
            ("(2,2)", msg['already_played_there']),
            ("quit", msg['successful_quit']),
            # Can't play without game FIXME improve response?
            ("(1,1)", msg['didnt_understand']),
            ("new", msg['new_game']),
            # Value out of range FIXME improve response?
            ("(1,5)", msg['didnt_understand']),
            # Value out of range FIXME improve response?
            ("0,1", msg['didnt_understand']),
            # Sequence of moves to show valid input formats:
            ("1,1", msg['after_1_1']),
            ("2, 1", msg['after_2_1']),
            ("(1,3)", msg['after_1_3']),
            ("3,2", msg['after_3_2']),
            ("2,3", msg['after_2_3_draw']),
            # Game already over; can't quit FIXME improve response?
            ("quit", msg['didnt_understand']),
            ("new", msg['new_game']),
            ("1,1", msg['after_1_1']),
            ("2,3", msg['after_2_3_try_lose']),
            ("2,1", msg['after_2_1_lost']),
            # Game already over; can't quit FIXME improve response?
            ("quit", msg['didnt_understand']),
        ]

        with patch('zulip_bots.bots.tictactoe.tictactoe.random.choice') as choice:
            choice.return_value = [2, 2]
            self.verify_dialog(conversation)
