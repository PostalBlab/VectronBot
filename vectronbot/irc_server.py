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

class IRCServer():
    class IRCChannel():
        def __init__(self, irc_server, channel, channel_password=None):
            self.channel = channel
            self.password = channel_password
            self.irc_server = irc_server
            self.bridge = None

        def send_message(self, message):
            self.irc_server.irc_connection_thread.send_message(self.channel, message)

        def token_received(self, from_user, token):
            self.bridge.irc_token_received(from_user, token)

        def message_received(self, from_user, message):
            self.bridge.irc_message_received(from_user, message)

        def is_user_op(self, nick):
            if nick in self.irc_server.irc_connection_thread._bot.channels[self.channel].modes['@']:
                return True
            return False

    def __init__(self, description, host, port=6697, ssl=True, password=None):
        self.description = description
        self.host = host
        self.port = port
        self.ssl = ssl
        self.password = password
        self.channels = {}
        self.irc_connection_thread = None

    def add_channel(self, channel, channel_password=None):
        irc_channel = IRCServer.IRCChannel(self, channel, channel_password)
        self.channels[channel] = irc_channel
        return irc_channel

    def remove_channel(self, channel):
        del self.channels[channel]
