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

import time
import logging
import threading
import urllib, urllib.request
import hashlib
import os
import random
import string
from PIL import Image
from os import listdir
from os.path import isfile, join, isdir


class FileHandler:

    def download(self, url, tg_group_id, vectronconfig):
        group_path = hashlib.md5(str(tg_group_id).encode('UTF-8')).hexdigest()
        outputdir = os.path.join(vectronconfig['webserver_directory'], group_path)
        os.makedirs(outputdir, exist_ok=True)

        file_name = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(15))
        file_extension = os.path.splitext(url)[1]

        full_path = os.path.join(group_path, file_name + file_extension)

        urllib.request.urlretrieve(url, os.path.join(vectronconfig['webserver_directory'], full_path))

        if (os.path.splitext(url)[1] == '.webp'):
            FileHandler.convert_webp_to_png(os.path.join(vectronconfig['webserver_directory'], full_path),
                                            os.path.join(vectronconfig['webserver_directory'], group_path, file_name))
            full_path = full_path.replace('.webp', '.png')
        return full_path

    def convert_webp_to_png(self, filename, destination):
        im = Image.open(filename)
        im.save(destination + '.png', 'PNG')


class CronDelete(threading.Thread):

    def __init__(self, vectronconfig):
        self._webserver_directory = vectronconfig['webserver_directory']
        self._webserver_data_retention = vectronconfig['webserver_data_retention']
        threading.Thread.__init__(self)

    def run(self):
        # this method works fine. we dont need to be super precise for data retention
        while True:
            self.clean_web_directory()
            time.sleep(60 * 5)

    def clean_web_directory(self):
        current_time = time.time()
        subdirs = [join(self._webserver_directory, f) for f in listdir(self._webserver_directory) if
                   isdir(join(self._webserver_directory, f))]
        for directory in subdirs:
            onlyfiles = [join(directory, f) for f in listdir(directory) if isfile(join(directory, f))]
            for single_file in onlyfiles:
                st = os.path.getmtime(single_file)
                if (st + (60 * self._webserver_data_retention)) < current_time:
                    logging.debug('Deleting file %s' % single_file)
                    try:
                        os.unlink(single_file)
                    except Exception:
                        logging.exception('Could not delete %s' % single_file)
