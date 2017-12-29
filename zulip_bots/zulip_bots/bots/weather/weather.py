# See readme.md for instructions on running this code.
import requests
import json
import logging

from typing import Any, Dict

class WeatherHandler(object):
    def initialize(self, bot_handler: Any) -> None:
        self.api_key = bot_handler.get_config_info('weather')['key']
        self.response_pattern = 'Weather in {}, {}:\n{:.2f} F / {:.2f} C\n{}'

        self.check_api_key()

    def check_api_key(self) -> None:
        url = 'http://api.openweathermap.org/data/2.5/weather?q=nyc&APPID=' + self.api_key
        test_response = requests.get(url)

        try:
            test_response_data = test_response.json()

            error_response = 'Invalid API key. Please see http://openweathermap.org/faq#error401 for more info.'
            if test_response_data['cod'] == 401 and test_response_data['message'] == error_response:
                logging.error('API Key not valid. Please see doc.md to find out how to get it.')
        except KeyError:
            pass

    def usage(self) -> str:
        return '''
            This plugin will give info about weather in a specified city
            '''

    def handle_message(self, message: Dict[str, str], bot_handler: Any) -> None:
        help_content = '''
            This bot returns weather info for specified city.
            You specify city in the following format:
            city, state/country
            state and country parameter is optional(useful when there are many cities with the same name)
            For example:
            @**Weather Bot** Portland
            @**Weather Bot** Portland, Me
            '''.strip()

        if (message['content'] == 'help') or (message['content'] == ''):
            response = help_content
        else:
            url = 'http://api.openweathermap.org/data/2.5/weather?q=' + message['content'] + '&APPID='
            r = requests.get(url + self.api_key)
            if r.json()['cod'] == "404":
                response = "Sorry, city not found"
            else:
                response = format_response(r, message['content'], self.response_pattern)

        bot_handler.send_reply(message, response)


def format_response(text: Any, city: str, response_pattern: str) -> str:
    j = text.json()
    city = j['name']
    country = j['sys']['country']
    fahrenheit = to_fahrenheit(j['main']['temp'])
    celsius = to_celsius(j['main']['temp'])
    description = j['weather'][0]['description'].title()

    return response_pattern.format(city, country, fahrenheit, celsius, description)


def to_celsius(temp_kelvin: float) -> float:
    return int(temp_kelvin) - 273.15


def to_fahrenheit(temp_kelvin: float) -> float:
    return int(temp_kelvin) * (9. / 5.) - 459.67

handler_class = WeatherHandler
