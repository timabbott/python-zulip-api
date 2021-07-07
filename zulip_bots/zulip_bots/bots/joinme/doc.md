# Joinme Bot

With joinme bot, you can start meetings with your team
 without having to leave Zulip.

## Setup

1. See [Joinme's developer docs](https://developer.join.me/docs) for
 setting up an account and registering the app.

1. Supply your credentials, namely `client_id`, `client_secret`
 and `redirect_uri` in `joinme.conf` file.

## Usage

To start a meeting, following steps are needed:

1. Run `@botname start meeting` and bot will respond with a
 link that asks for permission of user to view the personal URL.
 **NOTE**: *Login is required.*

1. Then, run `@botname confirm {authorization_url}` where
 *{authorization_url}* is the URL shown in the browser after
 authorizing Joinme.

1. The URL will expire in one minute. If so, just go back to step 1.

1. Finally, the bot will post a link to the newly created meeting.

*Take a look at this [Example](https://goo.gl/KDs3kL)*
