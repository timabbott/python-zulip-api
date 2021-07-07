import re
import requests
from typing import Any, Dict

TOPIC_REGEX = re.compile('^Bug (?P<bug_number>.+)$')

HELP_REGEX = re.compile('help$')

HELP_RESPONSE = '''
**help**

`help` returns this short help

**comment**

With no argument, by default, a new comment is added to the bug that is associated to the topic.
For example, on topic Bug 123,

you:

  > @**Bugzilla** A new comment

Then `A new comment` is added to bug 123
'''


class BugzillaHandler(object):
    '''
    A docstring documenting this bot.
    '''

    def usage(self):
        return '''
        Bugzilla Bot uses the Bugzilla REST API v1 to interact with Bugzilla. In order to use
        Bugzilla Bot, `bugzilla.conf` must be set up. See `doc.md` for more details.
        '''

    def initialize(self, bot_handler: Any) -> None:
        config = bot_handler.get_config_info('bugzilla')

        site = config.get('site')
        api_key = config.get('api_key')
        if not site:
            raise KeyError('No `site` was specified')
        if not api_key:
            raise KeyError('No `api_key` was specified')

        self.site = site
        self.api_key = api_key

    def handle_message(self, message: Dict[str, str], bot_handler: Any) -> None:
        content = message.get('content')
        topic = message.get('subject')

        if HELP_REGEX.match(content):
            self.handle_help(message, bot_handler)
            return None

        try:
            bug_number = self.extract_bug_number(topic)
        except ValueError:
            bot_handler.send_reply(message, 'Unsupported topic: ' + topic)
            return None

        comment = content
        self.handle_comment(bug_number, comment, message, bot_handler)

    def handle_help(self, message: Dict[str, str], bot_handler: Any) -> None:
        bot_handler.send_reply(message, HELP_RESPONSE)

    def handle_comment(self, bug_number: str, comment: str, message: Dict[str, str], bot_handler: Any) -> None:
        url = '{}/rest/bug/{}/comment'.format(self.site, bug_number)
        requests.post(url,
                      json=self.make_comment_json(comment))

    def make_comment_json(self, comment: str) -> Any:
        json = {
            'api_key': self.api_key,
            'comment': comment
        }
        return json

    def extract_bug_number(self, topic: str) -> Any:
        topic_match = TOPIC_REGEX.match(topic)

        if not topic_match:
            raise ValueError
        else:
            return topic_match.group('bug_number')


handler_class = BugzillaHandler
