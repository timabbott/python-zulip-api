# IRC <--> Zulip bridge

## Usage

```
./irc-mirror.py --irc-server=IRC_SERVER --channel=<CHANNEL> --nickname=<NICK> --stream=<STREAM> [optional args]
```

`--stream` is a Zulip stream.  
`--topic` is a Zulip topic, is optionally specified, defaults to "IRC".  
`--nickserv-pw` is the IRC nick password.

IMPORTANT: Make sure the bot is subscribed to the relevant Zulip stream!!

Specify your Zulip API credentials and server in a ~/.zuliprc file or using the options.

NOTE: Currently, when you send a message from IRC for the first time, you will encounter a "Read time out" connection error. This is expected and currently we are fixing the bug. However, the subsequent messages will be relayed successfully, and so the bridge should work just fine.
NOTE: If you encounter this error message
`AttributeError: 'AioReactor' object has no attribute 'scheduler'`,
simply restart the mirror until you don't encounter the error. This is a known bug.

## Example

```
./irc-mirror.py --irc-server=irc.freenode.net --channel='#python-mypy' --nickname=irc_mirror \
--stream='test here' --topic='#mypy' \
--site="https://chat.zulip.org" --user=<bot-email> \
--api-key=<bot-api-key>
```
