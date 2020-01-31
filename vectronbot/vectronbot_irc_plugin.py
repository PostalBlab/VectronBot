# -*- coding: utf-8 -*-
#
# VectronBot - Telegram - IRC bridge
# Copyright (C) 2016-2017  Daniel Hoffmann
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import irc3
import irc3d
import threading
import logging
from irc3.plugins.command import command
from vectronbot.config import config


@irc3.plugin
class VectronBotIRCPlugin:
    requires = [
        'irc3.plugins.core',
        'irc3.plugins.command'
    ]

    def __init__(self, bot):
        self.connected = threading.Event()
        self.token_callback = None
        self.message_callback = None
        self.bot = bot
        self.log = self.bot.log

    @command
    def t(self, mask, target, args):
        """Send to Telegram command
            %%t <words>...
        """
        if self.message_callback:
            self.message_callback(target, mask.nick, ' '.join(args['<words>']))

    @command
    def token(self, mask, target, args):
        """Receive security token to confirm the bridge
            %%token <words>...
        """
        if self.token_callback:
            self.token_callback(target, mask.nick, ' '.join(args['<words>']))

    @irc3.extend
    def set_t_callback(self, callback):
        self.message_callback = callback

    @irc3.extend
    def set_token_callback(self, callback):
        self.token_callback = callback

    @irc3.extend
    def send_message(self, target, message):
        """Send a message to the IRC
        """
        self.bot.loop.call_soon_threadsafe(self.bot.privmsg, target, message, True)

    @irc3.extend
    def part_threadsafe(self, channel):
        self.bot.loop.call_soon_threadsafe(self.bot.part, channel)

    @irc3.extend
    def join_channel_threadsafe(self, channel):
        self.bot.loop.call_soon_threadsafe(self.bot.join, channel)

    @irc3.extend
    def wait_for_connect(self):
        self.connected.wait()

    @irc3.event(irc3.rfc.KICK)
    def bot_kicked(self, **kw):
        logging.debug(kw)
        self.bot.irc_connection.kicked(kw)

    def connection_lost(self):
        self.connected.clear()
        self.bot.irc_connection.connection_lost()

    def server_ready(self):
        logging.debug('Connection made')
        self.connected.set()
        import time
        time.sleep(5)
        self.bot.irc_connection.rejoin_all_channel()

    @irc3.event(r'(@(?P<tags>\S+) )?:(?P<ns>NickServ)!NickServ@services.'
                r' NOTICE (?P<nick>\S+) :This nickname is registered.*')
    def register(self, ns=None, nick=None, **kw):
        password = config.nickserv_password
        self.bot.loop.call_soon_threadsafe(self.bot.privmsg, ns, 'identify %s %s' % (nick, password), True)
