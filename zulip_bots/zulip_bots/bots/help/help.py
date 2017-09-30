# See readme.md for instructions on running this code.

class HelpHandler(object):

    META = {
        'name': 'Help',
        'default_commands_enabled': False,
    }

    def usage(self):
        return '''
            This plugin will give info about Zulip to
            any user that types a message saying "help".

            This is example code; ideally, you would flesh
            this out for more useful help pertaining to
            your Zulip instance.
            '''

    def handle_message(self, message, bot_handler):
        help_content = "Info on Zulip can be found here:\nhttps://github.com/zulip/zulip"
        bot_handler.send_reply(message, help_content)

handler_class = HelpHandler
