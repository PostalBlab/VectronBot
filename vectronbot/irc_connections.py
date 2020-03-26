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

import logging
import irc3
import threading
import irc3.config
from database import DatabaseConnection

class IRCConnections:
    class IRCConnection(threading.Thread):
        def __init__(self, irc_server, vectronconfig):
            self._vectronconfig = vectronconfig
            self.irc_server = irc_server
            self.irc_server.irc_connection_thread = self
            threading.Thread.__init__(self)

            self._bot = None
            self.irc_bot_nickname = vectronconfig['irc_bot_nickname']

            config = dict(
                nick=self.irc_bot_nickname,
                host=irc_server.host,
                port=irc_server.port,
                ssl=irc_server.ssl,
                conf_async=False,
                ssl_verify='CERT_NONE',
                includes=['irc3.plugins.core', 'irc3.plugins.command', 'irc3.plugins.userlist', 'vectronbot_irc_plugin']
            )

            self._bot = irc3.IrcBot(**config)
            self._bot.set_t_callback(self.t_callback)
            self._bot.set_token_callback(self.token_callback)
            self._bot.irc_connection = self

        def token_callback(self, channel, from_user, token):
            try:
                self.irc_server.channels[channel].token_received(from_user, token)
            except KeyError:
                logging.debug('irc token callback KeyError')

        def t_callback(self, channel, from_user, message):
            try:
                self.irc_server.channels[channel].message_received(from_user, message)
            except KeyError:
                logging.debug('irc message callback KeyError')

        def run(self):
            try:
                self._bot.run(forever=True)
            except RuntimeError:
                logging.debug('Event loop is running')

        def join_channel(self, channel, only_add=False):
            irc_channel = self.irc_server.add_channel(channel)
            if not only_add:
                self.wait_for_connect()
                self._bot.join_channel_threadsafe(channel)
            return irc_channel

        def send_message(self, channel, message):
            self._bot.send_message(channel, message)

        def wait_for_connect(self):
            self._bot.wait_for_connect()

        def disconnect_channel(self, channel):
            self._bot.part_threadsafe(channel)

        def kicked(self, kw):
            self.irc_server.channels[kw['channel']].bridge.kicked_from_channel(
                kw['channel'],
                kw['data']
            )
            self._bot.join_channel_threadsafe(kw['channel'])

        def connection_lost(self):
            self.rejoin_all_channel()

        def rejoin_all_channel(self):
            # try to join all previous channels
            for key, channel in self.irc_server.channels.items():
                self._bot.join_channel_threadsafe(channel.channel)

    def __init__(self, vectronconfig):
        self._vectronconfig = vectronconfig
        self.connections = {}

    def get_irc_connection(self, description):
        if description in self.connections:
            return self.connections[description]
        return None

    def get_or_create_irc_server_by_description(self, description):
        if description in self.connections:
            return self.connections[description]
        dbc = DatabaseConnection()
        irc_server = dbc.get_irc_server_by_descripton(description)

        irc_connection = IRCConnections.IRCConnection(irc_server, self._vectronconfig)
        self.connections[irc_server.description] = irc_connection
        irc_connection.start()

        logging.debug('New IRC Connection to %s', irc_server.description)
        return irc_connection
