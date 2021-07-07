# Bugzilla bot

This bot allows to update directly Bugzilla from Zulip

## Setup

To use Bugzilla Bot, first set up `bugzilla.conf`. `bugzilla.conf` takes 2 options:
 - site (the site like `https://bugs.xxx.net` that includes both the protocol and the domain)
 - api_key (a Bugzilla API key)

 Example:
 ```
 [bugzilla]
site = https://bugs.site.net
api_key = xxxx
 ```


## Usage

Run this bot as described
[here](https://zulipchat.com/api/running-bots#running-a-bot).

Use this bot with the following command

`@mentioned-bot <action>` in a topic that is named `Bug 123` where 123 is the bug number

### comment

With no argument, by default, a new comment is added to the bug that is associated to the topic.
For example, on topic Bug 123,

you:

  > @**Bugzilla** A new comment

Then `A new comment` is added to bug 123
