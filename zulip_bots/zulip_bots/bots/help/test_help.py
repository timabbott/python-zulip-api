#!/usr/bin/env python

from zulip_bots.test_lib import StubBotTestCase

from typing import Any

class TestHelpBot(StubBotTestCase):
    bot_name = "help"

    def test_bot(self) -> None:
        help_text = "Info on Zulip can be found here:\nhttps://github.com/zulip/zulip"
        requests = ["", "help", "Hi, my name is abc"]

        dialog = [
            (request, help_text)
            for request in requests
        ]

        self.verify_dialog(dialog)
