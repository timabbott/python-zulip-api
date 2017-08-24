#!/usr/bin/env python

from __future__ import absolute_import
from __future__ import print_function

from zulip_bots.test_lib import BotTestCase
from zulip_bots.lib import StateHandler


class TestIncrementorBot(BotTestCase):
    bot_name = "incrementor"

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
        state_handler = StateHandler()
        self.assert_bot_response(dict(messages[0], content=""), {'content': "1"},
                                 'send_reply', state_handler)
#        self.assert_bot_response(dict(messages[0], content=""), {'message_id': 5, 'content': "2"},
#                                 'update_message', state_handler)
