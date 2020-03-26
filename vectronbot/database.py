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

import sqlite3
import logging
from irc_server import IRCServer

class DatabaseConnection:
    def __init__(self):
        self._connection = sqlite3.connect('vectronbot.db', check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._cursor = self._connection.cursor()

    def create_tables(self):
        # create tables if they do not exist
        self._cursor.execute('''
            CREATE TABLE IF NOT EXISTS irc_server (
            	description VARCHAR NOT NULL,
                visible INTEGER NOT NULL DEFAULT 1,
            	host VARCHAR NOT NULL,
            	port INTEGER NOT NULL,
            	ssl BOOLEAN NOT NULL,
            	password VARCHAR,
            	PRIMARY KEY (description),
            	CHECK (ssl IN (0, 1)),
                CHECK (visible IN (0, 1))
            );
        ''')
        self._cursor.execute('''
            CREATE TABLE IF NOT EXISTS irc_channel (
            	channel VARCHAR NOT NULL,
            	password VARCHAR,
            	irc_server_description INTEGER NOT NULL,
            	PRIMARY KEY (channel, irc_server_description),
            	FOREIGN KEY(irc_server_description) REFERENCES irc_server (description)
            );

        ''')
        self._cursor.execute('''
            CREATE TABLE IF NOT EXISTS bridge (
            	tg_id INTEGER NOT NULL,
            	token VARCHAR NOT NULL,
            	validated BOOLEAN NOT NULL,
            	irc_channel VARCHAR,
            	irc_server_description VARCHAR,
            	PRIMARY KEY (tg_id),
            	FOREIGN KEY(irc_channel, irc_server_description) REFERENCES irc_channel (channel, irc_server_description),
            	CHECK (validated IN (0, 1))
            );

        ''')

        self._cursor.execute('''
            CREATE TABLE IF NOT EXISTS secondary_bridge (
            	tg_id INTEGER NOT NULL,
            	token VARCHAR NOT NULL,
            	validated BOOLEAN NOT NULL,
            	primary_tg_id INTEGER NOT NULL,
            	PRIMARY KEY (tg_id),
            	CHECK (validated IN (0, 1))
            );

        ''')

    def add_secondary_bridge(self, secondary_bridge):
        if self.bridge_exists(secondary_bridge.bridge):
            self._cursor.execute('''
                INSERT INTO
                    secondary_bridge
                (tg_id, token, validated, primary_tg_id)
                    VALUES
                (?, ?, ?, ?)

            ''', (secondary_bridge.tg_group_id, secondary_bridge.token, secondary_bridge.validated,
                  secondary_bridge.bridge.tg_group_id))
            self._connection.commit()

    def set_secondary_bridge_validation(self, secondary_bridge):
        try:
            self._cursor.execute('UPDATE secondary_bridge SET validated=? WHERE tg_id=?',
                                 ((1 if secondary_bridge.validated else 0), secondary_bridge.tg_group_id,))
            self._connection.commit()
        except Exception as e:
            logging.debug(e)

    def get_all_secondary_bridges(self, bridge):
        self._cursor.execute('SELECT * FROM secondary_bridge WHERE primary_tg_id = ?', (bridge.tg_group_id,))
        lines = self._cursor.fetchall()
        secondary_bridges = {}
        for line in lines:
            secondary_bridges[line['tg_id']] = bridge.Bridge.SecondaryBridge(line['tg_id'], line['validated'], line['token'],
                                                                      bridge)
        return secondary_bridges

    def delete_all_secondary_bridges(self, tg_group_id):
        self._cursor.execute('DELETE FROM secondary_bridge WHERE primary_tg_id = ?', (tg_group_id,))

    def delete_secondary_bridge(self, secondary_bridge, commit=False):
        self._cursor.execute('DELETE FROM secondary_bridge WHERE tg_id = ? ', (secondary_bridge.tg_group_id,))
        if commit:
            self._connection.commit()

    def add_irc_server(self, irc_server, visible=True):
        if not self.irc_server_exists(irc_server.description):
            self._cursor.execute('''
                INSERT INTO
                    irc_server
                (description, host, port, ssl, password, visible)
                    VALUES
                (?, ?, ?, ?, ?, ?)

            ''', (
            irc_server.description, irc_server.host, irc_server.port, irc_server.ssl, irc_server.password, visible))
            self._connection.commit()

    def get_all_irc_server_descriptions(self, only_visible=True):
        servers = []
        qry = 'SELECT description FROM irc_server WHERE visible=1' if only_visible == True else 'SELECT description FROM irc_server'
        res = self._cursor.execute(qry)
        lines = self._cursor.fetchall()
        for line in lines:
            servers.append(line['description'])
        return servers

    def irc_server_exists(self, description):
        res = self._cursor.execute('SELECT description FROM irc_server WHERE description = ?', (description,))
        line = self._cursor.fetchone()
        if line is None:
            return False
        return True

    def get_irc_server_by_descripton(self, description):
        res = self._cursor.execute('SELECT * FROM irc_server WHERE description = ?', (description,))
        line = self._cursor.fetchone()
        if line is None:
            return None
        irc_server = IRCServer(line['description'], line['host'], line['port'], line['ssl'], line['password'])
        return irc_server

    def add_irc_channel(self, irc_channel, commit=False):
        if self.get_irc_server_by_descripton(irc_channel.irc_server.description) is None:
            logging.debug('Invalid IRC Server supplied')
            return
        if not self.irc_channel_exists(irc_channel):
            self._cursor.execute('''
                INSERT INTO
                    irc_channel
                (channel, password, irc_server_description)
                    VALUES
                (?, ?, ?)

            ''', (irc_channel.channel, irc_channel.password, irc_channel.irc_server.description))
            if commit:
                self._connection.commit()

    def irc_channel_exists(self, irc_channel):
        res = self._cursor.execute('SELECT channel FROM irc_channel WHERE channel=? and irc_server_description=?',
                                   (irc_channel.channel, irc_channel.irc_server.description))
        line = self._cursor.fetchone()
        if line:
            return True
        return False

    def delete_irc_channel(self, irc_channel):
        self._cursor.execute('DELETE FROM irc_channel WHERE channel=? and irc_server_description=?',
                             (irc_channel.channel, irc_channel.irc_server.description))

    def add_bridge(self, bridge):
        self.add_irc_channel(bridge.irc_channel, False)
        if not self.bridge_exists(bridge):
            self._cursor.execute('''
                INSERT INTO
                    bridge
                (tg_id, token, validated, irc_channel, irc_server_description)
                    VALUES
                (?, ?, ?, ?, ?)

            ''', (bridge.tg_group_id, bridge.token, bridge.validated, bridge.irc_channel.channel,
                  bridge.irc_channel.irc_server.description))
            self._connection.commit()

    def bridge_exists(self, bridge):
        res = self._cursor.execute('SELECT tg_id FROM bridge WHERE tg_id=?', (bridge.tg_group_id,))
        line = self._cursor.fetchone()
        if line:
            return True
        return False

    def delete_bridge(self, bridge):
        self.delete_all_secondary_bridges(bridge.tg_group_id)
        self._cursor.execute('DELETE FROM bridge WHERE tg_id=?', (bridge.tg_group_id,))
        self.delete_irc_channel(bridge.irc_channel)
        self._connection.commit()

    def set_bridge_validation(self, bridge):
        try:
            self._cursor.execute('UPDATE bridge SET validated=? WHERE tg_id=?',
                                 ((1 if bridge.validated else 0), bridge.tg_group_id,))
            self._connection.commit()
        except Exception as e:
            logging.debug(e)

    def get_all_bridges(self):
        # tg_group_id, irc_server_description, channel, token, validated=False, save_to_db=False
        res = self._cursor.execute('SELECT tg_id, irc_server_description, irc_channel, token, validated FROM bridge')
        bridges = self._cursor.fetchall()
        return bridges

    def irc_channel_alredy_bridged(self, channel, irc_server_description):
        self._cursor.execute('SELECT * FROM bridge WHERE irc_server_description = ? AND irc_channel = ?',
                             (irc_server_description, channel))
        line = self._cursor.fetchone()
        if line is None:
            return False
        return True

    def get_primary_group_id_by_irc_data(self, channel, irc_server_description):
        self._cursor.execute('SELECT tg_id FROM bridge WHERE irc_server_description = ? AND irc_channel = ?',
                             (irc_server_description, channel))
        line = self._cursor.fetchone()
        if line is None:
            return 0
        return line['tg_id']
