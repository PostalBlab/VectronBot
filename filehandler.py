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

import urllib, urllib.request
import hashlib
import os
from PIL import Image
import random
import string
from config import config
from os import listdir
import os
from os.path import isfile, join, isdir
import time
import logging
import threading

class FileHandler:

    DOWNLOAD_PATH=config.webserver_directory

    def download(url, tg_group_id):
        group_path = hashlib.md5(str(tg_group_id).encode('UTF-8')).hexdigest()
        if not os.path.exists(FileHandler.DOWNLOAD_PATH + group_path):
            os.makedirs(FileHandler.DOWNLOAD_PATH + group_path)

        file_name = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(15))
        file_extension = os.path.splitext(url)[1]

        full_path = group_path + '/' + file_name + file_extension

        urllib.request.urlretrieve (url, FileHandler.DOWNLOAD_PATH + full_path)

        if(os.path.splitext(url)[1] == '.webp'):
            FileHandler.convert_webp_to_png(FileHandler.DOWNLOAD_PATH + full_path, FileHandler.DOWNLOAD_PATH + group_path + '/' + file_name)
            full_path = full_path.replace('.webp', '.png')
        return full_path

    def convert_webp_to_png(filename, destination):
        webpname, webpextension = os.path.splitext(filename)
        im = Image.open(filename)
        im.save(destination + '.png', 'PNG')

class CronDelete(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        #this method works fine. we dont need to be super precise for data retention
        while True:
            self.clean_web_directory()
            time.sleep(60 * 5)


    def clean_web_directory(self):
        current_time = time.time()
        subdirs =  [join(config.webserver_directory, f) for f in listdir(config.webserver_directory) if isdir(join(config.webserver_directory, f))]
        for directory in subdirs:
            onlyfiles = [join(directory, f) for f in listdir(directory) if isfile(join(directory, f))]
            for single_file in onlyfiles:
                st = os.path.getmtime(single_file)
                if (st + (60 * config.webserver_data_retention)) < current_time:
                    logging.debug('Deleting file %s' % single_file)
                    try:
                        os.unlink(single_file)
                    except Exception as e:
                        logging.debug('Could not delete %s' % single_file)
                        logging.debug(str(e))
