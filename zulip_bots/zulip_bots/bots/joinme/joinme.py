import json
import requests
import socket
from configparser import ConfigParser
from typing import Any

class JoinmeHandler(object):
    def usage(self) -> str:
        return '''
         This bot will post a link to joinme call. Mention the bot and it will
         give out instructions.
        '''

    def handle_message(self, message: Any, bot_handler: Any) -> None:
        self.config_info = bot_handler.get_config_info('joinme')
        if 'ZISSHUDBUNIq' not in message['content']:
            # The state, a special string to identify which type of URL it is.
            payload = {'client_id': self.config_info['key'],
                       'scope': 'user_info scheduler start_meeting',
                       'redirect_uri': self.config_info['callback_url'],
                       'state': 'ZISSHUDBUNIq', 'response_type': 'code'}
            r = requests.get('https://secure.join.me/api/public/v1/auth/oauth2', params=payload)
            if str(r) == '<Response [200]>':
                content = "Please click the link below to log in and authorise " \
                          "Joinme:\n {} \nAnd please copy and send the url shown " \
                          "in browser after clicking accept. Don't forget to @-mention me!".format(r.url)

            else:
                content = "Please check if you have entered the correct API key and " \
                          "callback URL in joinme.conf."
        else:
            authorization_code = message['content']
            authorization_code = authorization_code.split('=')
            authorization_code = authorization_code[1].split('&')

            payload = {"client_id": self.config_info['key'],
                       "client_secret": self.config_info['secret'],
                       "code": authorization_code[0],
                       "redirect_uri": self.config_info['callback_url'],
                       "grant_type": "authorization_code"}
            req = requests.post('https://secure.join.me/api/public/v1/auth/token', data = payload)

            token = json.loads(req.text)
            if 'error' in token:
                content = 'The session has expired. Please start again by @-mention Joinme bot.'

            else:
                token = token['access_token']
                s = socket.gethostbyname(socket.gethostname())

                headers = {'Authorization': 'Bearer {}'.format(token),
                           'Content-Type': 'application/json',
                           'X-Originating-Ip': s}
                data = {"startWithPersonalUrl": 'false'}

                req_json = requests.post('https://api.join.me/v1/meetings/start',
                                         headers = headers, data = json.dumps(data))
                req_json = req.json()
                content = "Click this link to join the call:\n {}".format(req['presenterLink'])

        bot_handler.send_reply(message, content)

handler_class = JoinmeHandler
