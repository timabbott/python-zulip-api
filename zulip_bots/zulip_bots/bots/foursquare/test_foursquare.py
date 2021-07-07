from unittest.mock import patch
from zulip_bots.test_lib import BotTestCase
from requests.exceptions import ConnectionError

class TestFoursquareBot(BotTestCase):
    bot_name = "foursquare"
    config = {
        "client_id": "token",
        "client_secret": "secret",
        "v": "20180316",
        "near": "place",
        "limit": "5"
    }

    help_message = '''
Foursquare bot helps you find venues near your specified locations.
Simply run: `@botname query` and bot will return a list of venues matching your query.
'''

    def test_bot_responds_to_empty_message(self) -> None:
        self.verify_reply('', self.help_message)

    def test_help_message(self) -> None:
        self.verify_reply('', self.help_message)

    def test_error(self) -> None:
        bot_response = "Some error occured. Please try again :confused:\n \
For help, try **@botname help**"
        with self.mock_config_info(self.config), \
                self.mock_http_conversation('test_error'):
                    self.verify_reply('place', bot_response)

    def test_success(self) -> None:
        bot_response = "Places near place are:\n"
        result_array = [
            "\n**name1**\n- *Category*: 1\n- *Address*: address, 1\n\n",
            "\n**name2**\n- *Category*: 2\n- *Address*: address, 2\n\n",
            "\n**name3**\n- *Category*: 3\n- *Address*: address, 3\n\n",
            "\n**name4**\n- *Category*: 4\n- *Address*: address, 4\n\n",
            "\n**name5**\n- *Category*: 5\n- *Address*: address, 5\n\n"
        ]
        bot_response += ''.join(result_array)
        with self.mock_config_info(self.config), \
                self.mock_http_conversation('test_success'):
                    self.verify_reply('place', bot_response)

    def test_connection_error(self) -> None:
        with self.mock_config_info(self.config), \
                patch('requests.get', side_effect=ConnectionError()), \
                patch('logging.exception'):
            self.verify_reply('place', "Uh-Oh, couldn\'t process the request \
right now.\nPlease try again later")
