from zulip_bots.test_lib import BotTestCase

class TestHelpBot(BotTestCase):
    bot_name = "joinme"  # type: str

    def test_login(self) -> None:
        bot_response = "Please click the link below to log in and authorise " \
                       "Joinme:\n None \nAnd please copy and send the url shown " \
                       "in browser after clicking accept. Don't forget to @-mention me!"
        with self.mock_config_info({'key': '1234567890', 'callback_url': 'https://callback.com'}), \
                self.mock_http_conversation('test_login'):
            self.verify_reply('', bot_response)

    def test_bot_responds_to_empty_message(self) -> None:
        # It works the same as test_login
        pass

    def test_expired(self) -> None:
        bot_response = 'The session has expired. Please start again by @-mention ' \
                       'Joinme bot.'
        sent = 'https://developer.join.me/io-docs/oauth2callback?code=szn3hvd8t9y9kzuepw52kjhe&state=ZISSHUDBUNIq'
        with self.mock_config_info({'key': '1234567890', 'callback_url': 'https://callback.com', 'secret': '2345678901'}), \
                self.mock_http_conversation('test_expired'):
            self.verify_reply(sent, bot_response)
