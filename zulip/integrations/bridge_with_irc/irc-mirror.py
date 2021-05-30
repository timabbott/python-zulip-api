#!/usr/bin/env python3
#
# EXPERIMENTAL
# IRC <=> Zulip mirroring bot
#

import argparse
import zulip
import sys
import traceback

usage = """./irc-mirror.py --irc-server=IRC_SERVER --channel=<CHANNEL> --nickname=<NICK> --stream=<STREAM> [optional args]

Example:

./irc-mirror.py --irc-server=irc.freenode.net --channel='#test' --nickname=username --stream='test' --topic='#mypy'

--stream is a Zulip stream.
--topic is a Zulip topic, is optionally specified, defaults to "IRC".
--nickserv-pw is a password for the nickserv, is optionally specified.

Specify your Zulip API credentials and server in a ~/.zuliprc file or using the options.
"""

if __name__ == "__main__":
    parser = zulip.add_default_arguments(argparse.ArgumentParser(usage=usage), allow_provisioning=True)
    parser.add_argument('--irc-server', default=None)
    parser.add_argument('--port', default=6667)
    parser.add_argument('--nickname', default=None)
    parser.add_argument('--channel', default=None)
    parser.add_argument('--stream', default="general")
    parser.add_argument('--topic', default="IRC")
    parser.add_argument('--nickserv-pw', default='')

    options = parser.parse_args()
    # Setting the client to irc_mirror is critical for this to work
    options.client = "irc_mirror"
    zulip_client = zulip.init_from_options(options)
    try:
        from irc_mirror_backend import IRCBot
    except ImportError:
        traceback.print_exc()
        print("You have unsatisfied dependencies. Install all missing dependencies with "
              "{} --provision".format(sys.argv[0]))
        sys.exit(1)

    if options.irc_server is None or options.nickname is None or options.channel is None:
        parser.error("Missing required argument")

    nickname = options.nickname
    bot = IRCBot(zulip_client, options.stream, options.topic, options.channel,
                 nickname, options.irc_server, options.nickserv_pw, options.port)
    bot.start()
