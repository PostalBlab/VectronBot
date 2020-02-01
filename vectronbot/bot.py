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

import sys
import logging
import argparse
from vectronbot.tg_bot import TGBot
from vectronbot.database import DatabaseConnection
from vectronbot.filehandler import CronDelete
from vectronbot.irc_server import IRCServer

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s: %(message)s',
                    handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger('vectronbot')


def start_tg_bot():
    parser = argparse.ArgumentParser(description='TG / IRC bridge bot')
    parser.add_argument('--config', metavar='path', type=str, required=True, help='path to config file')
    parser.add_argument('--debug', dest='debug', action='store_true', required=False, default=False,
                        help='Activate debugging output')
    cliargs = parser.parse_args()

    if cliargs.debug:
        logger.setLevel(logging.DEBUG)
        logger.info('Loglevel set to DEBUG')

    vectronconfig = vectronbot.config.load_from_file(cliargs.config)
    tg_bot = TGBot(vectronconfig)

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

    # delete old files if the data retention is > 0
    if vectronconfig['webserver_data_retention'] > 0:
        cron_delete = CronDelete(vectronconfig)
        cron_delete.start()

    tg_bot.start_webhook()


if __name__ == "__main__":
    start_tg_bot()
