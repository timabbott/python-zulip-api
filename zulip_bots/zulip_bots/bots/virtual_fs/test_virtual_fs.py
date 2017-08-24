#!/usr/bin/env python

from __future__ import absolute_import
from __future__ import print_function

from zulip_bots.test_lib import BotTestCase
from zulip_bots.lib import StateHandler

class TestVirtualFsBot(BotTestCase):
    bot_name = "virtual_fs"

    def test_bot(self):
        help_txt = ('foo_sender@zulip.com:\n\nThis bot implements a virtual file system for a stream.\n'
                    'The locations of text are persisted for the lifetime of the bot\n'
                    'running, and if you rename a stream, you will lose the info.\n'
                    'Example commands:\n\n```\n'
                    '@mention-bot sample_conversation: sample conversation with the bot\n'
                    '@mention-bot mkdir: create a directory\n'
                    '@mention-bot ls: list a directory\n'
                    '@mention-bot cd: change directory\n'
                    '@mention-bot pwd: show current path\n'
                    '@mention-bot write: write text\n'
                    '@mention-bot read: read text\n'
                    '@mention-bot rm: remove a file\n'
                    '@mention-bot rmdir: remove a directory\n'
                    '```\n'
                    'Use commands like `@mention-bot help write` for more details on specific\ncommands.\n')
        expected = {
            "cd /home": "foo_sender@zulip.com:\nERROR: invalid path",
            "mkdir home": "foo_sender@zulip.com:\ndirectory created",
            "pwd": "foo_sender@zulip.com:\n/",
            "help": help_txt,
            "help ls": "foo_sender@zulip.com:\nsyntax: ls <optional_path>",
            "": help_txt,
        }
        self.check_expected_responses(expected)

        expected = [
            ("help", help_txt),
            ("help ls", "foo_sender@zulip.com:\nsyntax: ls <optional_path>"),
            ("", help_txt),
            ("pwd", "foo_sender@zulip.com:\n/"),
            ("cd /home", "foo_sender@zulip.com:\nERROR: invalid path"),
            ("mkdir home", "foo_sender@zulip.com:\ndirectory created"),
            ("cd /home", "foo_sender@zulip.com:\nCurrent path: /home/"),
        ]

        state_handler = StateHandler()
        self.check_expected_responses(expected, state_handler = state_handler)
