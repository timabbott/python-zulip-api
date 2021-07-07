from typing import Any, Dict
import  re
import os
import subprocess



class SnoozeBotHandler:


    def usage(self) -> str:
        return '''
        Snoozebot is a reminder tool that will message you at your requested time in the future. Snoozebot
        accepts three formats to set reminders.

        FORMAT:

        1) '# time'
           Example: '2 minutes.'

           With this format, Snoozebot is using the 'now +# time' syntax
           for the At command. If that means nothing to you, no worries, here is an example of what you would type in a
           zulip reply: @**snoozebot** 4 days. Minutes, days, weeks, months, and years are all acceptable for the time
           variable in this format.

        2) 'time day'
           Example: '@**snoozebot** 8:00AM Monday.'

           The days of the week, as well as 'tomorrow' and 'today' are acceptable, as in '@**snoozebot** 10:00PM today.'

        3) 'time month day'
           Example: '10:00am Jul 31'

           This format will set a reminder at a specific date and time. Each month is abbreviated to three characters.

        MESSAGE LOCATION:

        1) Message Snoozebot in the topic you want to be reminded of.

           If you message Snoozebot from a topic, Snoozebot
           will mention you in a PM at the set time. The message will be 'Ping! @**USER** #**stream>topic**. You may
           click the link to stream/topic link to return to the referenced topic.

        2) Directly PM Snoozebot

           In this case, the reminder will not automatically contain a link, however,Snoozebot is set to echo back the
           whole message you originally wrote. That way, if you want to be reminded of a specific topic, you can simply
           copy and paste the zulip link for the topic into your message, and Snoozebot will regurgitate it back to you
           for your later use and reference. Example: @**snoozebot** Remind me of <zulip link> 10:00am Aug 1. Here, the
           PM you get on August 1st will be: 'Ping! @**USER** Remind me of <zulip link> 10:00am Aug 1.'

        NOTES:

          * Snoozebot will always immediately echo back to you "Ok, I'll remind you..." as a confirmation that the reminder
            was set. If this does not happen, Snoozebot probably crashed.
          * There is no way to unset the reminder.
          * Time must be ##:## -- the regex patter expects a colon.
          * The reminder always comes as a PM to prevent spamming other users with your own reminders.


        If you have any questions or feedback, please PM me on Zulip Community Chat. -- MLH
        '''

    def handle_message(self, message: Dict[str, Any], bot_handler: Any) -> None:

        # Setting up the regex patterns
        pattern1 = re.compile(r'(\b\d+\s(minute|hour|day|week|month|year)s?)', re.IGNORECASE)
        pattern2 = re.compile(r'(\b\d{1,2}:\d{2}\s?(AM|PM|am|pm)\s?(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|tomorrow|today))', re.IG
        NORECASE)
        pattern3 = re.compile(r'(\d{1,2}:\d{1,2}\s?(AM|PM)\s?(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s?\d{1,2})', re.IGNORECASE)

        # Setting up the Match variables)
        match = re.search(pattern1, message['content'])
        match2 = re.search(pattern2, message['content'])
        match3 = re.search(pattern3, message['content'])

        # Message related variables

        if message.get('stream_id'):
            stream_id = message.get('stream_id')
            stream_name = message.get('display_recipient')
            content = message['content']
            topic = message['subject']
            user = message['sender_full_name']
            sender = message['sender_email']
            heredoc = f"""END
                   zulip-send {sender} --message 'Ping! @**{user}** #**{stream_name}>{topic}**' --config-file ~/python-zulip-api/zulip_bots/zulip_bot
                   s/bots/snoozebot/zuliprc
                   END"""


        else:
            stream_id = None
            stream_name = None
            content = message['content']
            topic = message['subject']
            user = message['sender_full_name']
            sender = message['sender_email']
            heredoc = f"""END
                   zulip-send {sender} --message 'Ping! @**{user}** {content}' --config-file ~/python-zulip-api/zulip_bots/zulip_bots/bots/snoozebot/
                   zuliprc
                   END"""


        # Example of etting up At command with the pipe method instead...
        # zulip_send_command = zulip-send %(stream name) %(message name) %(message)
        # at_command = " %(zulip_send) | at %(time_input)"



        # Message handling
        if message['content'] == '':
            bot_response = "Please specify the **snooze interval**, such as '4 days'. For help, message me with 'help.'"
            bot_handler.send_reply(message, bot_response)
        elif message['content'] == 'help':
            bot_handler.send_reply(message, self.usage())
        else:
            if pattern1.search(message['content']) != None:

                x = match.group(1)
                z = "Ok, I'll remind you in " + x

                # Diagnostic print messages
                #print(message['content'])
                #print(message['stream_id'])
                #print(x[0])
                #print(y)
                #print(match)
                #print(match[0])
                #print(pattern1.search(message[content])
                #y.join(x)
                print(message)
                print(heredoc)

                # Snoozebot echos back to user
                bot_handler.send_reply(message, z)

                # This is where the At job will be called.
                os.system("at now +%s << %s" %(x, heredoc))
                emoji_name = 'alarm clock'
                bot_handler.react(message, emoji_name)

            elif pattern2.search(message['content']) != None:

                l = match2.group(1)
                n = "Ok, I'll remind you at " + l
                bot_handler.send_reply(message, n)
                os.system("at %s << %s" %(l, heredoc))

            elif pattern3.search(message['content']) != None:

                l = match3.group(1)
                n = "Ok, I'll remind you at " + l
                bot_handler.send_reply(message, n)
                os.system("at %s << %s" %(l, heredoc))
            else:
                bot_handler.send_reply(message, "Oops, that won't work. Message me with 'help' for help on how to use me.")
        return

handler_class = SnoozeBotHandler
