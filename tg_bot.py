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

from telegram.ext import Updater
import logging
from irc_connections import IRCConnections
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters, ConversationHandler, RegexHandler
from telegram import ChatMember, KeyboardButton, ReplyKeyboardMarkup
from database import DatabaseConnection
import string
import random
from bridge import Bridge
from filehandler import FileHandler
from config import config

class TGBot():

    CHOOSING_SERVER, CHOOSING_CHANNEL, CONNECT_CHANNEL, CREATE_SECONDARY_BRIDGE = range(4)
    DELETE_BRIDGE = range(1)

    DL_URL = config.webserver_url

    def __init__(self):
        self.bridges = {}
        self.irc_connections = IRCConnections()

        self.updater = Updater(token=config.tg_bot_token)
        self._tg_bot = self.updater.bot
        self.dispatcher = self.updater.dispatcher
        help_handler = ConversationHandler(
                entry_points=[CommandHandler('help', self.help)],
                states={},
                fallbacks=[]

        )

        conv_handler = ConversationHandler(
                entry_points=[CommandHandler('start', self.start)],

                states={
                    self.CHOOSING_SERVER: [MessageHandler(Filters.text,
                                                   self.choosing_server,
                                                   pass_user_data=True),
                                    ],
                    self.CHOOSING_CHANNEL: [MessageHandler(Filters.text,
                                                   self.choosing_channel,
                                                   pass_user_data=True),
                                    ],
                    self.CONNECT_CHANNEL: [MessageHandler(Filters.text,
                                                   self.connect_channel,
                                                   pass_user_data=True),
                                    ],
                    self.CREATE_SECONDARY_BRIDGE: [MessageHandler(Filters.text,
                                                   self.secondary_bridge,
                                                   pass_user_data=True),
                                    ],
                },

                fallbacks=[CommandHandler('cancel', self.done, pass_user_data=True)]
        )

        delete_conv_handler = ConversationHandler(
            entry_points=[CommandHandler('delete', self.delete_bridge_question)],

            states={
                self.DELETE_BRIDGE: [MessageHandler(Filters.text,
                                                self.delete_bridge,
                                                pass_user_data=True),
                                    ],

            },

            fallbacks=[CommandHandler('cancel', self.done, pass_user_data=True)]

        )

        self.dispatcher.add_handler(conv_handler)
        self.dispatcher.add_handler(delete_conv_handler)
        #self.dispatcher.add_handler(debug_conv_handler)
        self.dispatcher.add_handler(help_handler)

        message_handler = MessageHandler(Filters.text, self.message_received)
        photo_handler = MessageHandler(Filters.photo, self.photo_received)
        voice_handler = MessageHandler(Filters.voice, self.voice_received)
        document_handler = MessageHandler(Filters.document, self.document_received)
        video_handler = MessageHandler(Filters.video, self.video_received)
        sticker_handler = MessageHandler(Filters.sticker, self.sticker_received)
        audio_handler = MessageHandler(Filters.audio, self.audio_received)

        self.dispatcher.add_handler(message_handler)
        self.dispatcher.add_handler(photo_handler)
        self.dispatcher.add_handler(voice_handler)
        self.dispatcher.add_handler(document_handler)
        self.dispatcher.add_handler(video_handler)
        self.dispatcher.add_handler(sticker_handler)
        self.dispatcher.add_handler(audio_handler)

    def delete_bridge_question(self, bot, update):
        if self.bridge_exists(update.message.chat.id) or self.secondary_bridge_exists(update.message.chat.id):
            if update.message.chat.get_member(update.message.from_user.id).status != ChatMember.CREATOR:
                 bot.sendMessage(chat_id=update.message.chat_id, text="Only the creator is allowed to delete me!")
                 return ConversationHandler.END

            update.message.reply_text('Do you really want to delete the bridge?', reply_markup=self.yes_no_keyboard())
            return self.DELETE_BRIDGE

        bot.sendMessage(chat_id=update.message.chat_id, text="This Group is not part of a bridge!")
        return ConversationHandler.END

    def delete_bridge(self, bot, update, user_data):
        if update.message.text == 'yes':
            if self.bridge_exists(update.message.chat.id):
                dbc = DatabaseConnection()
                bridge = self.bridges[update.message.chat_id]
                dbc.delete_bridge(bridge)
                bridge.irc_channel.irc_server.irc_connection_thread.disconnect_channel(bridge.irc_channel.channel)
                del self.bridges[update.message.chat_id]
                update.message.reply_text('Done! The bridge is deleted.')
                return ConversationHandler.END
            elif self.secondary_bridge_exists(update.message.chat.id):
                dbc = DatabaseConnection()
                bridge = self.get_bridge_by_id(update.message.chat.id)
                secondary_bridge = bridge.secondary_bridges[update.message.chat.id]
                bridge.remove_secondary_bridge(secondary_bridge)
                dbc.delete_secondary_bridge(secondary_bridge, commit=True)
                update.message.reply_text('Done! The bridge is deleted.')
                return ConversationHandler.END
        elif update.message.text == 'no':
            update.message.reply_text('No? Ok...')
            return ConversationHandler.END
        else:
            update.message.reply_text('Error. This code should be unreachable')
            return ConversationHandler.END


    def send_message(self, tg_group_id, message):
        self._tg_bot.sendMessage(chat_id = tg_group_id, text = message  )

    def start_webhook(self):
        self.updater.start_webhook(listen=config.webhook_listen_ip,
                              port=config.webhook_port,
                              url_path=config.tg_bot_token,
                              key=config.webhook_ssl_key,
                              cert=config.webhook_ssl_cert,
                              webhook_url=config.webhook_url)

    def help(self, bot, update):
        update.message.reply_text(
            'If you need help you can contact my maintainer at @PostalDude'
        )
        return ConversationHandler.END

    def start(self, telegramBot, update):
        if not update.message.chat.type == 'group':
             telegramBot.sendMessage(chat_id=update.message.chat_id, text='You can only use me in a group!')
             return ConversationHandler.END
        if update.message.chat.get_member(update.message.from_user.id).status != ChatMember.CREATOR:
             telegramBot.sendMessage(chat_id=update.message.chat_id, text="Only the creator is allowed to configure me!")
             return ConversationHandler.END

        if self.bridge_exists(update.message.chat.id) or self.secondary_bridge_exists(update.message.chat.id):
            telegramBot.sendMessage(chat_id=update.message.chat_id, text="This Group is already part of a bridge. Abort!")
            return ConversationHandler.END

        servers = DatabaseConnection().get_all_irc_server_descriptions()
        update.message.reply_text('Hi! I\'m BridgeBot. If you can, you should host your own BridgeBot. This way you can ' +
            'change the config for e.g. preventing files from being deleted. You can get the code on github: https://github.com/PostalBlab/VectronBot. ' +
            'If you want to use this Bot, i need some informations. You can cancel this dialogue with /cancel ' +
            'Here is a list of all public supported irc servers. Please tell me which one you want to use. '
            'If your prefered server is not in the list you can contact the maintainer @PostalDude. He can also add hidden servers where only you know '
            'the needed description:\n' +
            '\n'.join('- {}'.format(k) for k in servers))
        return self.CHOOSING_SERVER

    def choosing_server(self, bot, update, user_data):
        user_data['tg_group_id'] = update.message.chat.id
        servers = DatabaseConnection().get_all_irc_server_descriptions(False)
        logging.debug(servers)
        if update.message.text in servers:
            user_data['irc_server_description'] = update.message.text
            update.message.reply_text('%s it is! To which channel should i connect? e.g. #telegram' % update.message.text)
            return self.CHOOSING_CHANNEL
        else:
            update.message.reply_text('Invalid Server. Try again!')
        return self.CHOOSING_SERVER

    def choosing_channel(self, bot, update, user_data):
        if not update.message.text.startswith('#'):
            update.message.reply_text('IRC channels have to begin with a #. Try again.')
            return self.CHOOSING_CHANNEL
        user_data['channel'] = update.message.text
        if self.bridge_exists(update.message.chat.id):
            telegramBot.sendMessage(chat_id=update.message.chat_id, text="This Group is already part of a bridge. Abort!")
            return ConversationHandler.END

        # test if the channel is already part of a bridge, if so offer a secondary bridge
        # which is only one way, tg->irc
        # this way you can post media without disturbing the whole primary group
        dbc = DatabaseConnection()
        if dbc.irc_channel_alredy_bridged(user_data['channel'], user_data['irc_server_description']):
            update.message.reply_text(
                'This channel is already party of a bridge. Would you like to create a secondary bridge?'
                ' This way you can post stuff in the IRC without disturbing the primary TG Group.',
                reply_markup=self.yes_no_keyboard()
            )
            return self.CREATE_SECONDARY_BRIDGE

        update.message.reply_text(
            'Thanks. Should i try to join %s on %s?' %
            (user_data['channel'], user_data['irc_server_description']),
            reply_markup=self.yes_no_keyboard()
        )

        return self.CONNECT_CHANNEL

    def secondary_bridge(self, bot, update, user_data):
        if update.message.text == 'yes':
            user_data['token'] = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(6))
            dbc = DatabaseConnection()
            primary_tg_id = dbc.get_primary_group_id_by_irc_data(user_data['channel'], user_data['irc_server_description'])
            secondary_bridge = Bridge.SecondaryBridge(user_data['tg_group_id'], False, user_data['token'], self.bridges[primary_tg_id])
            dbc.add_secondary_bridge(secondary_bridge)
            update.message.reply_text('To validate this secondary bridge, someone with +o has to paste this code into the channel: !token %s' % user_data['token'])
            return ConversationHandler.END

        elif update.message.text == 'no':
            update.message.reply_text('No? Ok... Abort!')
            return ConversationHandler.END
        else:
            update.message.reply_text('Error. This code should be unreachable')
            return ConversationHandler.END
        return ConversationHandler.END

    def connect_channel(self, bot, update, user_data):
        if update.message.text == 'yes':
            #https://stackoverflow.com/questions/2257441/random-string-generation-with-upper-case-letters-and-digits-in-python
            user_data['token'] = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(6))
            update.message.reply_text('''
                Ok. I am going to connect to the server...
            ''')
            if self.create_bridge_from_userdata(user_data):
                update.message.reply_text('I\'m connected to the server and joined the channel. Someone with +o has to paste this code into the channel: !token %s' % user_data['token'])
                return ConversationHandler.END
            else:
                update.message.reply_text('Something went wrong. Please contact nobody! ABORT')
                return ConversationHandler.END

        elif update.message.text == 'no':
            update.message.reply_text('No? Ok...')
            return ConversationHandler.END
        else:
            update.message.reply_text('Error. This code should be unreachable')
            return ConversationHandler.END

    def debug(self, bot, update):
        user_data = {}
        user_data['tg_group_id'] = update.message.chat.id
        user_data['irc_server_description'] = 'Freenode'
        user_data['channel'] = '#postest'
        user_data['token'] = 'yolo'
        if self.create_bridge_from_userdata(user_data):
            update.message.reply_text('I\'m connected to the server and joined the channel. Someone with +o has to paste this code into the channel: !token %s' % user_data['token'])
            return ConversationHandler.END
        else:
            update.message.reply_text('Something went wrong. Please contact nobody! ABORT')
            return ConversationHandler.END
        return ConversationHandler.END

    def done(self, bot, update, user_data):
        update.message.reply_text('KK THX BYE')
        user_data.clear()
        return ConversationHandler.END

    def create_bridge(self, tg_group_id, irc_server_description, channel, token, validated=False, save_to_db=False, only_add_channel=False):
        irc_connection = self.irc_connections.get_or_create_irc_server_by_description(irc_server_description)
        irc_channel = irc_connection.join_channel(channel, only_add=only_add_channel)
        bridge = Bridge(irc_channel, tg_group_id, validated, self, token)
        self.bridges[tg_group_id] = bridge
        if save_to_db:
            dbc = DatabaseConnection()
            dbc.add_bridge(bridge)
        return True

    def create_bridge_from_userdata(self, user_data):
        return self.create_bridge(user_data['tg_group_id'], user_data['irc_server_description'], user_data['channel'], user_data['token'], False, True)

    def yes_no_keyboard(self):
        keyboard = [[
            KeyboardButton('yes'),
            KeyboardButton('no')
        ]]

        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        return reply_markup


    def get_bridge_by_id(self, tg_group_id):
        if tg_group_id in self.bridges:
            return self.bridges[tg_group_id]
        else:
            for key, bridge in self.bridges.items():
                if tg_group_id in bridge.secondary_bridges:
                    return bridge
        raise KeyError

    def download_file(self, file_id, group_id):
        path = self._tg_bot.get_file(file_id)
        file_location = FileHandler.download(path.file_path, group_id)
        return file_location

    def bridge_exists(self, tg_id):
        if tg_id in self.bridges:
            return True
        return False

    def secondary_bridge_exists(self, tg_id):
        for key, bridge in self.bridges.items():
            if tg_id in bridge.secondary_bridges:
                return True
        return False

    def message_received(self, bot, update):
        try:
            bridge = self.get_bridge_by_id(update.message.chat_id)
            bridge.tg_message(update.message.from_user.first_name + ' ' + update.message.from_user.last_name, update.message.text)
        except KeyError as e:
            logging.debug('KeyError in tg_bot. Unknown group')
        except Exception as e:
            logging.debug('Whaaat')
            logging.debug(e)

    def photo_received(self, bot, update):
        try:
            bridge = self.get_bridge_by_id(update.message.chat_id)
            biggest = update.message.photo[0]
            #look for the biggest picture, thats what we want. the others are previews
            for photo in update.message.photo[1:]:
                if photo.file_size > biggest.file_size:
                    biggest = photo
            file_location = self.download_file(biggest.file_id, update.message.chat_id)
            bridge.tg_message(
                update.message.from_user.first_name + (' ' + update.message.from_user.last_name if update.message.from_user.last_name else ''),
                self.DL_URL + file_location + ' ' + update.message.caption
            )

        except Exception as e:
            logging.debug('photo_received: ' + str(e))

    def voice_received(self, bot, update):
        try:
            bridge = self.get_bridge_by_id(update.message.chat_id)
            file_location = self.download_file(update.message.voice.file_id, update.message.chat_id)
            bridge.tg_message(update.message.from_user.first_name + ' ' + update.message.from_user.last_name, self.DL_URL + file_location)

        except Exception as e:
            logging.debug('voice_received: ' + e)

    def document_received(self, bot, update):
        try:
            bridge = self.get_bridge_by_id(update.message.chat_id)
            file_location = self.download_file(update.message.document.file_id, update.message.chat_id)
            bridge.tg_message(update.message.from_user.first_name + ' ' + update.message.from_user.last_name, self.DL_URL + file_location)

        except Exception as e:
            logging.debug('document_received: ' + e)

    def sticker_received(self, bot, update):
        try:
            bridge = self.get_bridge_by_id(update.message.chat_id)
            file_location = self.download_file(update.message.sticker.file_id, update.message.chat_id)
            bridge.tg_message(update.message.from_user.first_name + ' ' + update.message.from_user.last_name, self.DL_URL + file_location)

        except Exception as e:
            logging.debug('sticker_received: ' + e)

    def video_received(self, bot, update):
        try:
            bridge = self.get_bridge_by_id(update.message.chat_id)
            file_location = self.download_file(update.message.video.file_id, update.message.chat_id)
            bridge.tg_message(update.message.from_user.first_name + ' ' + update.message.from_user.last_name, self.DL_URL + file_location)

        except Exception as e:
            logging.debug('video_received: ' + e)

    def audio_received(self, bot, update):
        try:
            bridge = self.get_bridge_by_id(update.message.chat_id)
            file_location = self.download_file(update.message.audio.file_id, update.message.chat_id)
            bridge.tg_message(update.message.from_user.first_name + ' ' + update.message.from_user.last_name, self.DL_URL + file_location)

        except Exception as e:
            logging.debug('audio_received: ' + e)
