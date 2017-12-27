#!/usr/bin/env python3

from zulip_bots.test_lib import BotTestCase

class TestVirtualFsBot(BotTestCase):
    bot_name = "virtual_fs"
    help_txt = ('foo@example.com:\n\nThis bot implements a virtual file system for a stream.\n'
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

    def test_commands_1(self) -> None:
        expected = [
            ("cd /home", "foo@example.com:\nERROR: invalid path"),
            ("mkdir home", "foo@example.com:\ndirectory created"),
            ("pwd", "foo@example.com:\n/"),
            ("help", self.help_txt),
            ("help ls", "foo@example.com:\nsyntax: ls <optional_path>"),
            ("", self.help_txt),
        ]
        self.verify_dialog(expected)

    def test_commands_2(self) -> None:
        expected = [
            ("help", self.help_txt),
            ("help ls", "foo@example.com:\nsyntax: ls <optional_path>"),
            ("", self.help_txt),
            ("pwd", "foo@example.com:\n/"),
            ("cd /home", "foo@example.com:\nERROR: invalid path"),
            ("mkdir home", "foo@example.com:\ndirectory created"),
            ("cd /home", "foo@example.com:\nCurrent path: /home/"),
        ]
        self.verify_dialog(expected)
