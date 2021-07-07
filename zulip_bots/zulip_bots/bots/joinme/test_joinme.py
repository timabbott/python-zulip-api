from typing import Any
from unittest.mock import patch
from zulip_bots.test_lib import BotTestCase

class TestHelpBot(BotTestCase):
    bot_name = "joinme"
    normal_config = {
        "client_id": "123456789",
        "scope": "user_info scheduler start_meeting",
        "redirect_uri": "https://callback.com",
        "state": "radomstringpassedforsecuritystandpoint",
        "response_type": "code"
    }
    token_config = {
        "client_id": "123456789",
        "code": "szn3hvd8t9y9kzuepw52kjhe",
        "grant_type": "authorization_code",
        "client_secret": "2345678901",
        "redirect_uri": "https://callback.com"
    }
    start_meeting_config = {
        "client_id": "123456789",
        "code": "szn3hvd8t9y9kzuepw52kjhe",
        "grant_type": "authorization_code",
        "client_secret": "2345678901",
        "redirect_uri": "https://callback.com",
        "startWithPersonalUrl": "false"
    }

    help_message = '''
This is Joinme bot.
You can start meetings by: **@botname start meeting** and \
then confirming by: **@botname confirm <authorization_code>**.
'''

    # Test for empty message response
    def test_bot_responds_to_empty_message(self) -> None:
        self.verify_reply('', self.help_message)

    # Test for help message response
    def test_help_message(self) -> None:
        self.verify_reply('help', self.help_message)

    # Test for successful link generation to initiate the flow
    def test_link_generated(self) -> None:
        bot_response = "Please click the link below to log in and authorize:\n \
None \n\n NOTE: Please copy and paste the URL shown \
in browser after clicking accept.\n Don't forget to prefix the URL with **@botname confirm**"
        with self.mock_config_info(self.normal_config), \
                self.mock_http_conversation('test_link_generated'):
            self.verify_reply('start meeting', bot_response)

    # Test for unsuccessful link generation
    def test_link_generation_failed(self) -> None:
        bot_response = "Please check if you have entered the correct API key and \
callback URL in `.conf` file."
        with self.mock_config_info(self.normal_config), \
                self.mock_http_conversation('test_link_generation_failed'):
            self.verify_reply('start meeting', bot_response)

    # Test for access_token expired
    def test_token_expired(self) -> None:
        bot_response = "The token has expired. Please start again by \
doing: **@botname start meeting**."
        with self.mock_config_info(self.token_config), \
                self.mock_http_conversation('test_token_expired'):
            self.verify_reply('confirm https://example.com?\
code=szn3hvd8t9y9kzuepw52kjhe&state=radomstringpassedforsecuritystandpoint', bot_response)

    # Test for access_token not granted
    def test_token_grant_failed(self) -> None:
        bot_response = "Ooops! Some error occured while generating access_token. \
Check your `.conf` file, try again regenerating authorization code."
        with self.mock_config_info(self.token_config), \
                self.mock_http_conversation('test_token_grant_failed'):
                    self.verify_reply('confirm https://example.com?\
code=szn3hvd8t9y9kzuepw52kjhe&state=radomstringpassedforsecuritystandpoint', bot_response)

    # Test for access_token granted and start_meeting successful
    @patch('zulip_bots.bots.joinme.joinme.socket.gethostbyname')
    @patch('zulip_bots.bots.joinme.joinme.get_token')
    def test_start_meeting_success(self, get_token: Any, gethostbyname: Any) -> None:
        link_var = "https://secure.join.me/API/Public/StartMeeting.aspx?token=1234567890"
        bot_response = "Click this link to join the call: {}".format(link_var)

        with self.mock_config_info(self.start_meeting_config), \
                self.mock_http_conversation('test_start_meeting_success'):
                    get_token.return_value = 1234567890
                    gethostbyname.return_value = "127.0.1.1"
                    self.verify_reply('confirm https://example.com?\
code=szn3hvd8t9y9kzuepw52kjhe&state=radomstringpassedforsecuritystandpoint', bot_response)

    # Test for wrong command given
    def test_wrong_command(self) -> None:
        bot_response = "Make sure you have typed it correctly. \
**@botname help** might help :simple_smile:"
        self.verify_reply('invalidCommand', bot_response)
