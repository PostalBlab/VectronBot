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

import configparser
import os.path
import logging

class Config:

    def __init__(self):
        ini_config = configparser.ConfigParser()
        if not os.path.isfile('config.ini'):
            logging.debug('config.ini not found')
            raise IOError
        ini_config.read('config.ini')

        self.tg_bot_token = ini_config['tg_bot']['token']

        self.webserver_url = ini_config['webserver']['url']
        self.webserver_directory = ini_config['webserver']['directory']
        self.webserver_data_retention = int(ini_config['webserver']['data_retention'])

        self.webhook_port = int(ini_config['webhook']['port'])
        self.webhook_url = ini_config['webhook']['url'] + ':{0}/{1}'.format(self.webhook_port, self.tg_bot_token)
        self.webhook_ssl_cert = ini_config['webhook']['ssl_cert']
        self.webhook_ssl_key = ini_config['webhook']['ssl_key']
        self.webhook_listen_ip = ini_config['webhook']['listen_ip']

        self.nickserv_password = ini_config['irc']['nickserv_password']
        self.irc_bot_nickname = ini_config['irc']['nickname']
config = Config()
