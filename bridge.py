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
import database

class Bridge():

    class SecondaryBridge():
        def __init__(self, tg_group_id, validated, token, bridge):
            self.bridge = bridge
            self.tg_group_id = tg_group_id
            self.validated = validated
            self.token = token
            self.bridge.add_secondary_bridge(self)

    def __init__(self, irc_channel, tg_group_id, validated, tg_bot, token):
        self.irc_channel = irc_channel
        self.irc_channel.bridge = self
        self.tg_group_id = tg_group_id
        self.validated = validated
        self.tg_bot = tg_bot
        self.token = token
        self.secondary_bridges = {}
        dbc = database.DatabaseConnection()
        dbc.get_all_secondary_bridges(self)


    def add_secondary_bridge(self, secondary_bridge):
        self.secondary_bridges[secondary_bridge.tg_group_id] = secondary_bridge

    def remove_secondary_bridge(self, secondary_bridge):
        del self.secondary_bridges[secondary_bridge.tg_group_id]

    def send_to_irc(self, user, message):
        if self.validated:
            for split_message in [message[i:i+400] for i in range(0, len(message), 400)]:
                self.irc_channel.send_message('<{}> {}'.format(user, split_message))

    def send_to_tg(self, user, message):
         if self.validated:
             self.tg_bot.send_message(self.tg_group_id, '<{}> {}'.format(user, message))

    def irc_token_received(self, from_user, token):
        if self.validated:
            # if the primary bridge is validated we check all the secondary bridges
            for key, secondary_bridge in self.secondary_bridges.items():
                if not secondary_bridge.validated and secondary_bridge.token == token:
                    secondary_bridge.validated = True
                    dbc = database.DatabaseConnection()
                    dbc.set_secondary_bridge_validation(secondary_bridge)
                    self.send_to_irc('system', 'Secondary bridge is now validated!')
                    return

            self.send_to_irc('system', 'Why? The Bridge is already validated')
            return

        if self.irc_channel.is_user_op(from_user) and self.token == token:
            self.set_validation()
            self.send_to_irc('system', 'Successfully registered the new bridge. Have fun!')
            self.send_to_tg('system', 'Successfully registered the new bridge. Have fun!')
        else:
            self.send_to_irc('system', 'The token is invalid and/or the sender is no operator.')

    def irc_message_received(self, from_user, message):
        self.send_to_tg(from_user, message)

    def set_validation(self):
        self.validated = True
        dbc = database.DatabaseConnection()
        dbc.set_bridge_validation(self)

    def tg_message(self, from_user, message):
        self.send_to_irc(from_user, message)

    def kicked_from_channel(self, channel, reason):
        self.send_to_tg('system', 'Someone kicked me from {0} with the reason: {1}'.format(channel, reason))
        self.send_to_tg('system', 'If you want to delete the bridge please use /delete')
