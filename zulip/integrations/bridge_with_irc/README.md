# IRC <--> Zulip bridge

For a how-to guide, please see:

https://zulipchat.com/integrations/doc/irc

## SSL warning

It can be tricky to get SSL to work, but if you are not using it, everyone's
chats may be leaking through the bridge for any MitM attack.

## Adding SSL certificates for IRC servers

This section could need a bit of additional experience and elaboration.

If your IRC server uses a CA that your system doesn't trust or some other
mechanism of self-signing, please consider adding that as a basic CA in your
system-wide platform. We have not written command-line options for storing
and trusting extra certificates for the bridge.

## Usage

```
./irc-mirror.py --irc-server=IRC_SERVER --channel=<CHANNEL> --nick-prefix=<NICK> --stream=<STREAM> [optional args]
```

`--stream` is a Zulip stream.  
`--topic` is a Zulip topic, is optionally specified, defaults to "IRC".  
`--nickserv-pw` is the IRC nick password.
`--no-ssl` leaks everything in free text

IMPORTANT: Make sure the bot is subscribed to the relevant Zulip stream!!

Specify your Zulip API credentials and server in a ~/.zuliprc file or using the options.

IMPORTANT: Note that "_zulip" will be automatically appended to the IRC nick provided, so make sure that your actual registered nick ends with "_zulip".

## Example

```
./irc-mirror.py --irc-server=irc.freenode.net --channel='#python-mypy' --nick-prefix=irc_mirror \
--stream='test here' --topic='#mypy' \
--site="https://chat.zulip.org" --user=<bot-email> \
--api-key=<bot-api-key>
```
