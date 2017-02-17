#!/usr/bin/env python3
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
from tg_bot import TGBot
from database import DatabaseConnection
from filehandler import CronDelete
from config import config
from irc_server import IRCServer

if __name__ == "__main__":

    tg_bot = TGBot()

    dbc = DatabaseConnection()
    dbc.create_tables()
    # irc_server = IRCServer('Freenode', 'chat.freenode.net')
    # dbc.add_irc_server(irc_server)

    # irc_server = IRCServer('Quakenet', 'irc.quakenet.org', port=6667, ssl=False)
    # dbc.add_irc_server(irc_server)
    # irc_server = IRCServer('IRCNet', 'open.ircnet.org', port=6666)
    # dbc.add_irc_server(irc_server)
    # irc_server = IRCServer('Undernet', 'eu.undernet.org', port=6667)
    # dbc.add_irc_server(irc_server)

    bridges = dbc.get_all_bridges()
    for bridge in bridges:
        tg_bot.create_bridge(
            bridge['tg_id'],
            bridge['irc_server_description'],
            bridge['irc_channel'],
            bridge['token'],
            bridge['validated'],
            only_add_channel=True
        )

    #delete old files if the data retention is > 0
    if config.webserver_data_retention > 0:
        cron_delete = CronDelete()
        cron_delete.start()

    tg_bot.start_webhook()
