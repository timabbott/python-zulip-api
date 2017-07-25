#!/usr/bin/env python
from __future__ import print_function
from __future__ import absolute_import

import logging
import argparse
import sys
import os
from types import ModuleType
from importlib import import_module
from os.path import basename, splitext

import six

from zulip_bots.lib import run_message_handler_for_bot
from zulip_bots.provision import provision_bot


def import_module_from_source(path, name=None):
    if name is None:
        name = splitext(basename(path))[0]

    if six.PY2:
        import imp
        module = imp.load_source(name, path)
        return module
    else:
        import importlib.util
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


def parse_args():
    usage = '''
        zulip-run-bot <bot_name>
        Example: zulip-run-bot followup
        (This program loads bot-related code from the
        library code and then runs a message loop,
        feeding messages to the library code to handle.)
        Please make sure you have a current ~/.zuliprc
        file with the credentials you want to use for
        this bot.
        See lib/readme.md for more context.
        '''

    parser = argparse.ArgumentParser(usage=usage)
    parser.add_argument('name',
                        action='store',
                        nargs='?',
                        default=None,
                        help='the name of an existing bot to run')

    parser.add_argument('--quiet', '-q',
                        action='store_true',
                        help='Turn off logging output.')

    parser.add_argument('--config-file',
                        action='store',
                        help='(alternate config file to ~/.zuliprc)')

    parser.add_argument('--path-to-bot',
                        action='store',
                        help='path to the file with the bot handler class')

    parser.add_argument('--force',
                        action='store_true',
                        help='Try running the bot even if dependencies install fails.')

    parser.add_argument('--provision',
                        action='store_true',
                        help='Install dependencies for the bot.')
    options = parser.parse_args()

    if not options.name and not options.path_to_bot:
        error_message = """
You must either specify the name of an existing bot or
specify a path to the file (--path-to-bot) that contains
the bot handler class.
"""
        parser.error(error_message)

    return options


def main():
    # type: () -> None
    options = parse_args()

    if options.path_to_bot:
        if options.provision:
            bot_dir = os.path.dirname(os.path.abspath(options.path_to_bot))
            provision_bot(bot_dir, options.force)
        lib_module = import_module_from_source(options.path_to_bot, name=options.name)
    elif options.name:
        if options.provision:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            bots_parent_dir = os.path.join(current_dir, "bots")
            bot_dir = os.path.join(bots_parent_dir, options.name)
            provision_bot(bot_dir, options.force)
        lib_module = import_module('zulip_bots.bots.{bot}.{bot}'.format(bot=options.name))

    if not options.quiet:
        logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    run_message_handler_for_bot(
        lib_module=lib_module,
        config_file=options.config_file,
        quiet=options.quiet
    )

if __name__ == '__main__':
    main()
