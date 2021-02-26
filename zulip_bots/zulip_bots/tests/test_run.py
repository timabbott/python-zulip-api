#!/usr/bin/env python3
import os
import sys
import entrypoints
import zulip_bots.run
from zulip_bots.lib import extract_query_without_mention
import unittest
from typing import Optional
from unittest import TestCase

from unittest import mock
from unittest.mock import patch


class TestDefaultArguments(TestCase):

    our_dir = os.path.dirname(__file__)
    path_to_bot = os.path.abspath(os.path.join(our_dir, '../bots/giphy/giphy.py'))
    packaged_bot_distro = entrypoints.Distribution("packaged-bot-source", "1.0.0")
    packaged_bot_entrypoint = entrypoints.EntryPoint("packaged_bot", "module_name", None, distro=packaged_bot_distro)

    @patch('sys.argv', ['zulip-run-bot', 'giphy', '--config-file', '/foo/bar/baz.conf'])
    @patch('zulip_bots.run.run_message_handler_for_bot')
    def test_argument_parsing_with_bot_name(self, mock_run_message_handler_for_bot: mock.Mock) -> None:
        with patch('zulip_bots.run.exit_gracefully_if_zulip_config_is_missing'):
            zulip_bots.run.main()

        mock_run_message_handler_for_bot.assert_called_with(bot_name='giphy',
                                                            config_file='/foo/bar/baz.conf',
                                                            bot_config_file=None,
                                                            lib_module=mock.ANY,
                                                            bot_source='source',
                                                            quiet=False)

    @patch('sys.argv', ['zulip-run-bot', path_to_bot, '--config-file', '/foo/bar/baz.conf'])
    @patch('zulip_bots.run.run_message_handler_for_bot')
    def test_argument_parsing_with_bot_path(self, mock_run_message_handler_for_bot: mock.Mock) -> None:
        with patch('zulip_bots.run.exit_gracefully_if_zulip_config_is_missing'):
            zulip_bots.run.main()

        mock_run_message_handler_for_bot.assert_called_with(
            bot_name='giphy',
            config_file='/foo/bar/baz.conf',
            bot_config_file=None,
            lib_module=mock.ANY,
            bot_source='source',
            quiet=False)

    @patch('sys.argv', ['zulip-run-bot', 'packaged_bot', '--config-file', '/foo/bar/baz.conf'])
    @patch('zulip_bots.run.run_message_handler_for_bot')
    def test_argument_parsing_with_zulip_bot_registry(self, mock_run_message_handler_for_bot: mock.Mock) -> None:
        with patch('zulip_bots.run.exit_gracefully_if_zulip_config_is_missing'):
            with patch('zulip_bots.finder.entrypoints.EntryPoint.load'):
                with patch('zulip_bots.finder.entrypoints.get_group_all', return_value = [self.packaged_bot_entrypoint]):
                    zulip_bots.run.main()

        mock_run_message_handler_for_bot.assert_called_with(
            bot_name='packaged_bot',
            config_file='/foo/bar/baz.conf',
            bot_config_file=None,
            lib_module=mock.ANY,
            bot_source='packaged-bot-source: 1.0.0',
            quiet=False)

    def test_adding_bot_parent_dir_to_sys_path_when_bot_name_specified(self) -> None:
        bot_name = 'helloworld'  # existing bot's name
        expected_bot_dir_path = os.path.join(
            os.path.dirname(zulip_bots.run.__file__),
            'bots',
            bot_name
        )
        self._test_adding_bot_parent_dir_to_sys_path(bot_qualifier=bot_name, bot_dir_path=expected_bot_dir_path)

    @patch('os.path.isfile', return_value=True)
    def test_adding_bot_parent_dir_to_sys_path_when_bot_path_specified(self, mock_os_path_isfile: mock.Mock) -> None:
        bot_path = '/path/to/bot'
        expected_bot_dir_path = '/path/to'
        self._test_adding_bot_parent_dir_to_sys_path(bot_qualifier=bot_path, bot_dir_path=expected_bot_dir_path)

    def _test_adding_bot_parent_dir_to_sys_path(self, bot_qualifier: str, bot_dir_path: str) -> None:
        with patch('sys.argv', ['zulip-run-bot', bot_qualifier, '--config-file', '/path/to/config']):
            with patch('zulip_bots.finder.import_module_from_source', return_value=mock.Mock()):
                with patch('zulip_bots.run.run_message_handler_for_bot'):
                    with patch('zulip_bots.run.exit_gracefully_if_zulip_config_is_missing'):
                        zulip_bots.run.main()

        self.assertIn(bot_dir_path, sys.path)

    @patch('os.path.isfile', return_value=False)
    def test_run_bot_by_module_name(self, mock_os_path_isfile: mock.Mock) -> None:
        bot_module_name = 'bot.module.name'
        mock_bot_module = mock.Mock()
        mock_bot_module.__name__ = bot_module_name
        with patch('sys.argv', ['zulip-run-bot', 'bot.module.name', '--config-file', '/path/to/config']):
            with patch('importlib.import_module', return_value=mock_bot_module) as mock_import_module:
                with patch('zulip_bots.run.run_message_handler_for_bot'):
                    with patch('zulip_bots.run.exit_gracefully_if_zulip_config_is_missing'):
                        zulip_bots.run.main()
                        mock_import_module.assert_called_once_with(bot_module_name)


class TestBotLib(TestCase):
    def test_extract_query_without_mention(self) -> None:

        def test_message(name: str, message: str, expected_return: Optional[str]) -> None:
            mock_client = mock.MagicMock()
            mock_client.full_name = name
            mock_message = {'content': message}
            self.assertEqual(expected_return, extract_query_without_mention(mock_message, mock_client))
        test_message("xkcd", "@**xkcd**foo", "foo")
        test_message("xkcd", "@**xkcd** foo", "foo")
        test_message("xkcd", "@**xkcd** foo bar baz", "foo bar baz")
        test_message("xkcd", "@**xkcd**         foo bar baz", "foo bar baz")
        test_message("xkcd", "@**xkcd** 123_) (/&%) +}}}l", "123_) (/&%) +}}}l")
        test_message("brokenmention", "@**brokenmention* foo", None)
        test_message("nomention", "foo", None)
        test_message("Max Mustermann", "@**Max Mustermann** foo", "foo")
        test_message(r"Max (Mustermann)#(*$&12]\]", r"@**Max (Mustermann)#(*$&12]\]** foo", "foo")

if __name__ == '__main__':
    unittest.main()
