import logging
import requests
from typing import Any, Dict
from requests.exceptions import ConnectionError

API_SEARCH_URL = "https://api.foursquare.com/v2/venues/search"

help_message = '''
Foursquare bot helps you find venues near your specified locations.
Simply run: `@botname query` and bot will return a list of venues matching your query.
'''

def get_foursquare_response(content: str, config: Dict[Any, Any]) -> str:
    client_id = config['client_id']
    client_secret = config['client_secret']
    query = content.strip()

    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "v": "20180316",
        "near": query,
        "limit": "5"
    }

    try:
        response = requests.get(API_SEARCH_URL, params=payload)
    except ConnectionError as e:
        logging.exception(str(e))
        return "Uh-Oh, couldn't process the request \
right now.\nPlease try again later"

    response = response.json()
    if response["meta"]["code"] == 200:
        result = "Places near {} are:\n".format(query)
        for place in response["response"]["venues"]:
            place_name = place["name"]
            if len(place['categories']) > 0:
                place_category = place["categories"][0]["name"]
            else:
                place_category = "Not specified"
            place_loc = ', '.join(place["location"]["formattedAddress"])
            result += "\n**{}**\n- *Category*: {}\n- *Address*: {}\n\n".format(place_name, place_category, place_loc)
        return result
    else:
        return "Some error occured. Please try again :confused:\n For help, try **@botname help**"


def get_foursquare_bot_response(content: str, config: Dict[str, str]) -> None:
    content = content.strip()
    if content == '' or content == 'help':
        return help_message
    else:
        result = get_foursquare_response(content, config)
        return result


class FoursquareHandler(object):
    '''
    With Foursquare bot, you can search for venues near a user
    specified location to a limit of 5.
    '''

    def initialize(self, bot_handler: Any) -> None:
        self.config_info = bot_handler.get_config_info('foursquare')

    def usage(self) -> str:
        return '''
            This plugin allows users to search for venues nearby a specified location,
            to a limit of 5.
            The name, address and category of the place will be outputted.
            It looks for messages starting with '@mention-bot'.

            If you need help, simply run: @mention-bot help
            '''

    def handle_message(self, message: Dict[str, str], bot_handler: Any) -> None:
        response = get_foursquare_bot_response(message['content'], self.config_info)
        bot_handler.send_reply(message, response)

handler_class = FoursquareHandler
