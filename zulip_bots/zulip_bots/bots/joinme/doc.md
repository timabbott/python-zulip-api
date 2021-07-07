# Joinme bot

The Joinme bot posts a link to a Joinme call when being mentioned.

## Setup

1. See [Joinme's developer docs](https://developer.join.me/docs) for setting up an account and
   registering the app.
2. Open `bots/joinme/joinme.conf` and replace the values of `url`, `secret` and
   `callback_url` with your credentials.
3. See [here](https://zulipchat.com/api/running-bots#running-a-bot) for description
   on how to run a bot.
4. You can run the bot by running the following command:

   `zulip-run-bot joinme --config-file ~/zuliprc-joinme --bot-config
   -file ~/zulip/python-zulip-api/zulip_bots/zulip_bots/bots/joinme/joinme.conf`

## Usage

1. @-mention it first and it will respond with a link that asks for permission
   to view the personal url and to start a new meeting. Login is required.

2. Then. @-mention the bot again with the URL shown in the browser after
   authorising Joinme.

3. The URL will expire in one minute. If so, just go back to step 1.

4. Finally, the bot will post a link to the newly created meeting.

[Example](https://goo.gl/BFKmXa)
