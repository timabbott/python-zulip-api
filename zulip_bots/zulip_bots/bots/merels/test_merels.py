from zulip_bots.test_lib import BotTestCase, DefaultTests
from zulip_bots.game_handler import GameInstance
from . libraries.constants import EMPTY_BOARD
from . libraries import interface
from . libraries import database

from typing import List, Tuple, Any

class TestMerelsBot(BotTestCase, DefaultTests):
    bot_name = 'merels'

    def test_no_command(self):
        message = dict(content='magic', type='stream', sender_email="boo@email.com", sender_full_name="boo")
        res = self.get_response(message)
        self.assertEqual(res['content'], 'You are not in a game at the moment.'' Type `help` for help.')

    # FIXME: Add tests for computer moves
    # FIXME: Add test lib for game_handler

    def test_determine_game_over_continue(self) -> None:
        board = EMPTY_BOARD
        players = ['Human', 'Human']
        expected_response = ''
        self._test_determine_game_over_continue(board, players, expected_response)

    def _test_determine_game_over_continue(self, board: List[List[int]], players: List[str], expected_response: str) -> None:
        model, message_handler = self._get_game_handlers()
        merelsGame = model(board)
        response = merelsGame.determine_game_over(players)
        self.assertEqual(response, expected_response)

    def test_determine_game_over_winning(self) -> None:
        board = EMPTY_BOARD
        players = ['Human', 'Human']
        expected_response = 'current turn'
        self._test_determine_game_over_winning(board, players, expected_response)

    def _test_determine_game_over_winning(self, board: List[List[int]], players: List[str], expected_response: str) -> None:
        model, message_handler = self._get_game_handlers()
        merelsGame = model(board)

        boardValues = "NONNONNONONNNONNNNONXOXN"
        grid = interface.construct_grid(boardValues)
        boardUpdated = interface.construct_board(grid)
        merels = database.MerelsStorage(merelsGame.topic, merelsGame.storage)
        merels.update_game('merels', 'O', 7, 2, boardUpdated, "", 0)
        response = merelsGame.determine_game_over(players)
        self.assertEqual(response, expected_response)

    def test_make_move(self) -> None:
        board = EMPTY_BOARD
        move = "put(0,0)"
        player_number = 0
        computer_move = False
        self._test_make_move(board, move, player_number, computer_move)

    def _test_make_move(self, board: List[List[int]], move: str, player_number: int, computer_move: bool=False) -> None:
        model, message_handler = self._get_game_handlers()
        merelsGame = model(board)
        response = merelsGame.make_move(move, player_number, computer_move)
        expected_response = merelsGame.current_board
        self.assertEqual(response, expected_response)

    # Test for unchanging aspects within the game
    # Player Color, Start Message, Moving Message
    def test_static_responses(self) -> None:
        model, message_handler = self._get_game_handlers()
        self.assertNotEqual(message_handler.get_player_color(0), None)
        self.assertNotEqual(message_handler.game_start_message(), None)
        self.assertEqual(message_handler.alert_move_message('foo', 'moved right'), 'foo :moved right')

    # Test to see if the attributes exist
    def test_has_attributes(self) -> None:
        model, message_handler = self._get_game_handlers()
        # Attributes from the Merels Handler
        self.assertTrue(hasattr(message_handler, 'parse_board') is not None)
        self.assertTrue(hasattr(message_handler, 'get_player_color') is not None)
        self.assertTrue(hasattr(message_handler, 'alert_move_message') is not None)
        self.assertTrue(hasattr(message_handler, 'game_start_message') is not None)
        self.assertTrue(hasattr(message_handler, 'alert_move_message') is not None)
        # Attributes from the Merels Model
        self.assertTrue(hasattr(model, 'determine_game_over') is not None)
        self.assertTrue(hasattr(model, 'contains_winning_move') is not None)
        self.assertTrue(hasattr(model, 'make_move') is not None)

    def test_parse_board(self) -> None:
        board = EMPTY_BOARD
        expectResponse = EMPTY_BOARD
        self._test_parse_board(board, expectResponse)

    def test_add_user_to_cache(self):
        self.add_user_to_cache("Name")

    def test_setup_game(self):
        self.setup_game()

    def add_user_to_cache(self, name: str, bot: Any=None) -> Any:
        if bot is None:
            bot, bot_handler = self._get_handlers()
        message = {
            'sender_email': '{}@example.com'.format(name),
            'sender_full_name': '{}'.format(name)}
        bot.add_user_to_cache(message)
        return bot

    def setup_game(self) -> None:
        bot = self.add_user_to_cache('foo')
        self.add_user_to_cache('baz', bot)
        instance = GameInstance(bot, False, 'test game', 'abc123', [
                                'foo@example.com', 'baz@example.com'], 'test')
        bot.instances.update({'abc123': instance})
        instance.start()
        return bot

    def _get_game_handlers(self) -> Tuple[Any, Any]:
        bot, bot_handler = self._get_handlers()
        return bot.model, bot.gameMessageHandler

    def _test_parse_board(self, board: str, expected_response: str) -> None:
        model, message_handler = self._get_game_handlers()
        response = message_handler.parse_board(board)
        self.assertEqual(response, expected_response)
