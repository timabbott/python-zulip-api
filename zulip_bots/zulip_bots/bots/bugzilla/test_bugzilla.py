from typing import Any, Dict
from zulip_bots.test_lib import BotTestCase, DefaultTests


class TestBugzillaBot(BotTestCase, DefaultTests):
    bot_name = 'bugzilla'

    MOCK_CONFIG_INFO = {
        'site': 'https://bugs.net',
        'api_key': 'kkk'
    }

    MOCK_HELP_RESPONSE = '''
**help**

`help` returns this short help

**comment**

With no argument, by default, a new comment is added to the bug that is associated to the topic.
For example, on topic Bug 123,

you:

  > @**Bugzilla** A new comment

Then `A new comment` is added to bug 123
'''

    def make_request_message(self, content: str) -> Dict[str, Any]:
        message = super().make_request_message(content)
        message['subject'] = "Bug 123"
        return message

    def handle_message_only(self, request: str) -> Dict[str, Any]:
        bot, bot_handler = self._get_handlers()
        message = self.make_request_message(request)
        bot_handler.reset_transcript()
        bot.handle_message(message, bot_handler)

    def test_bot_responds_to_empty_message(self) -> None:
        pass

    def _test_invalid_config(self, invalid_config, error_message) -> None:
        with self.mock_config_info(invalid_config), \
                self.assertRaisesRegexp(KeyError, error_message):
            bot, bot_handler = self._get_handlers()

    def test_config_without_site(self) -> None:
        config_without_site = {
            'api_key': 'kkk',
        }
        self._test_invalid_config(config_without_site,
                                  'No `site` was specified')

    def test_config_without_api_key(self) -> None:
        config_without_api_key = {
            'site': 'https://bugs.xx',
        }
        self._test_invalid_config(config_without_api_key,
                                  'No `api_key` was specified')

    def test_comment(self) -> None:
        with self.mock_config_info(self.MOCK_CONFIG_INFO), \
                self.mock_http_conversation('test_comment'):
            self.handle_message_only('a comment')

    def test_help(self) -> None:
        with self.mock_config_info(self.MOCK_CONFIG_INFO):
            self.verify_reply('help', self.MOCK_HELP_RESPONSE)


class TestBugzillaBotWrongTopic(BotTestCase, DefaultTests):
    bot_name = 'bugzilla'

    MOCK_CONFIG_INFO = {
        'site': 'https://bugs.net',
        'api_key': 'kkk'
    }

    MOCK_COMMENT_INVALID_TOPIC_RESPONSE = 'Unsupported topic: kqatm2'

    def make_request_message(self, content: str) -> Dict[str, Any]:
        message = super().make_request_message(content)
        message['subject'] = "kqatm2"
        return message

    def test_bot_responds_to_empty_message(self) -> None:
        pass

    def test_no_bug_number(self) -> None:
        with self.mock_config_info(self.MOCK_CONFIG_INFO):
            self.verify_reply(
                'a comment', self.MOCK_COMMENT_INVALID_TOPIC_RESPONSE)
