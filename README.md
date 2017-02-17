This bot creates a bridge between a Telegram group and an IRC channel. Everything posted in the Telegram group will be send to the IRC. Photos, files etc. gets downloaded and a link is posted in the IRC (max 20MB, data gets deleted after several hours). Users in the irc have to put a leading "!t" to their messages to send them to the group.
Sometimes you want to send a message or file to the irc, but you don't want to disturb the whole group. There is a solution! Create a group with the bot and do the normal registration. If there is already a primary bridge the bot asks you if you want to create a secondary bridge. The secondary bridge is one-way only. Everything you send to the Telegram group gets posted in the IRC but nothing gets from the IRC to the group, only to the primary group.

# Dependencies

* Pillow (PIL for python3)
* irc3
* python-telegram-bot
* sqlite3


# Requirements

* Telegram Bot API key. Please visit https://core.telegram.org/bots#6-botfather
* Webserver to make downloaded files available
* The bot needs to be able to join groups. Send /setjoingroups to https://telegram.me/BotFather
* The bot needs to be able to read all messages. Send /setprivacy to https://telegram.me/BotFather

# Installation

Copy config.ini.example to config.ini and enter all the needed informations.
First time starting, the bot creates the sqlite3 database. After this you can
add servers with this code snippet:

```python
from tg_bot import TGBot
from database import DatabaseConnection
from irc_server import IRCServer

dbc = DatabaseConnection()
dbc.create_tables()
irc_server = IRCServer('Freenode', 'chat.freenode.net')
dbc.add_irc_server(irc_server)
```

# Usage
Start bot.py Invite the bot into a group and send to the group /start

# Telegram commands
* start - Create a bridge between this group and an irc channel
* delete - Deletes an existing bridge or secondary bridge
* help - Show the contact of the maintainer
