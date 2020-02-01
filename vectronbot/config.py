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


def load_from_file(configfile_path):
    ini_config = configparser.ConfigParser()
    ini_config.read(configfile_path)
    vectronconfig = dict()

    vectronconfig['tg_bot_token'] = ini_config['tg_bot']['token']

    vectronconfig['webserver_url'] = ini_config['webserver']['url']
    vectronconfig['webserver_directory'] = ini_config['webserver']['directory']
    vectronconfig['webserver_data_retention'] = int(ini_config['webserver']['data_retention'])

    vectronconfig['webhook_port'] = int(ini_config['webhook']['port'])
    vectronconfig['webhook_url'] = ini_config['webhook']['url'] + ':{0}/{1}'.format(vectronconfig['webhook_port'],
                                                                                    vectronconfig['tg_bot_token'])
    vectronconfig['webhook_ssl_cert'] = ini_config['webhook']['ssl_cert']
    vectronconfig['webhook_ssl_key'] = ini_config['webhook']['ssl_key']
    vectronconfig['webhook_listen_ip'] = ini_config['webhook']['listen_ip']

    vectronconfig['nickserv_password'] = ini_config['irc']['nickserv_password']
    vectronconfig['irc_bot_nickname'] = ini_config['irc']['nickname']

    return vectronconfig
