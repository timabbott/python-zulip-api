import socket
import requests
from typing import Any, Dict, Text

help_message = '''
This is Joinme bot.
You can start meetings by: **@botname start meeting** and then \
confirming by: **@botname confirm <authorization_code>**.
'''

def get_start_meeting_response(message_content: str, config_info: Dict[str, str]) -> str:
    client_id = config_info['client_id']
    redirect_uri = config_info['redirect_uri']

    payload = {
        'client_id': client_id,
        'scope': 'user_info scheduler start_meeting',
        'redirect_uri': redirect_uri,
        'state': 'radomstringpassedforsecuritystandpoint',
        'response_type': 'code'
    }
    r = requests.get('https://secure.join.me/api/public/v1/auth/oauth2', params=payload)

    if r.status_code == 200:
        content = u"Please click the link below to log in and authorize:\n \
{} \n\n NOTE: Please copy and paste the URL shown \
in browser after clicking accept.\n Don't forget to prefix the URL with **@botname confirm**".format(r.url)
    elif "ExitPointId" in r.json():
        content = "Please check if you have entered the correct API key and \
callback URL in `.conf` file."
    return content

# Function to get access_token
def get_token(message_content: str, config_info: Dict[str, str]) -> str:
    auth_code = message_content.split('=')[1].split('&')[0]
    client_id = config_info['client_id']
    redirect_uri = config_info['redirect_uri']
    client_secret = config_info['client_secret']

    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": auth_code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    res = requests.post('https://secure.join.me/api/public/v1/auth/token', json=payload).json()

    if "error" in res:
        content = "Ooops! Some error occured while generating access_token. \
Check your `.conf` file, try again regenerating authorization code."
    elif "message" in res:
        content = "The token has expired. Please start again by doing: **@botname start meeting**."
    elif res["access_token"]:
        content = res["access_token"]
    return content

'''
This function calls get_token function to get an access_token which
it uses to make a POST start_meeting request to the Joinme API
'''
def get_confirm_meeting_start(message_content: str, config_info: Dict[str, str]) -> str:
    token = get_token(message_content, config_info)
    if len(str(token)) > 30:
        result = token   # Returns message if access_token is not granted or gets expired.
    else:
        get_host = socket.gethostbyname(socket.gethostname())
        headers = {
            'Authorization': 'Bearer {}'.format(token),
            'Content-Type': 'application/json',
            'X-Originating-Ip': get_host
        }
        data = {"startWithPersonalUrl": 'false'}

        start_meeting_res = requests.post('https://api.join.me/v1/meetings/start',
                                          headers=headers,
                                          json=data).json()
        result = "Click this link to join the call: {}".format(start_meeting_res["presenterLink"])
    return result

# This function applies a simple logic to call
# different functions in response to different commands
def get_joinme_response(message_content: str, config_info: Dict[str, str]) -> str:
    message_content = message_content.strip()
    if message_content == '' or message_content == 'help':
        return help_message

    if message_content == 'start meeting':
        result = get_start_meeting_response(message_content, config_info)
        return result
    elif message_content.startswith('confirm'):
        result = get_confirm_meeting_start(message_content, config_info)
        return result
    return "Make sure you have typed it correctly. **@botname help** might help :simple_smile:"

class JoinmeHandler(object):
    '''
    This is joinme bot. Now you can start meetings with your team without
having to leave Zulip.
    '''

    def initialize(self, bot_handler: Any) -> None:
        self.config_info = bot_handler.get_config_info('joinme')

    def usage(self) -> str:
        return '''This bot will post a link to joinme call.
 Give appropriate commands and it will give out instructions.'''

    def handle_message(self, message: Dict[str, str], bot_handler: Any) -> None:
        response = get_joinme_response(message['content'], self.config_info)
        bot_handler.send_reply(message, response)

handler_class = JoinmeHandler
