#!/usr/bin/python3
#    Copyright (C) 2016  derpeter
#    derpeter@berlin.ccc.de
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import configparser
import socket
import sys
import logging
import os
import subprocess

from api_client.republica_client import RPClient
from api_client.c3tt_rpc_client import C3TTClient
from api_client.voctoweb_client import VoctowebClient
from api_client.youtube_client import YoutubeAPI
import api_client.twitter_client as twitter
from model.ticket_module import Ticket


class Publisher:
    """
    This is the main class for the publishing application
    modeled from the c3 VOC publishing system, April 2017
    """
    def __init__(self):
        # load config
        if not os.path.exists('client.conf'):
            raise IOError("Error: config file not found")

        self.config = configparser.ConfigParser()
        self.config.read('client.conf')

        # set up logging
        logging.addLevelName(logging.WARNING, "\033[1;33m%s\033[1;0m" % logging.getLevelName(logging.WARNING))
        logging.addLevelName(logging.ERROR, "\033[1;41m%s\033[1;0m" % logging.getLevelName(logging.ERROR))
        logging.addLevelName(logging.INFO, "\033[1;32m%s\033[1;0m" % logging.getLevelName(logging.INFO))
        logging.addLevelName(logging.DEBUG, "\033[1;85m%s\033[1;0m" % logging.getLevelName(logging.DEBUG))

        self.logger = logging.getLogger()

        ch = logging.StreamHandler(sys.stdout)
        if self.config['general']['debug']:
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s {%(filename)s:%(lineno)d} %(message)s')
        else:
            formatter = logging.Formatter('%(asctime)s - %(message)s')

        ch.setFormatter(formatter)
        self.logger.addHandler(ch)
        self.logger.setLevel(logging.DEBUG)

        level = self.config['general']['debug']
        if level == 'info':
            self.logger.setLevel(logging.INFO)
        elif level == 'warning':
            self.logger.setLevel(logging.WARNING)
        elif level == 'error':
            self.logger.setLevel(logging.ERROR)
        elif level == 'debug':
            self.logger.setLevel(logging.DEBUG)

        #######################################
        # rewrite this to work with the RePublica Website?
        rp_event_id=self.config['republica']['event_id']
        rp_year=self.config['republica']['year']

        # get the session ID from commandline
        rp_session_id = raw_input('Enter Session ID: ')

        if self.config['republica']['host'] == "None":
            self.host = socket.getfqdn()
        else:
            self.host = self.config['republica']['host']

        self.from_state = self.config['republica']['from_state'] # needed?
        self.to_state = self.config['republica']['to_state'] # needed?

        try:
            self.rp = RPClient(self.config['republica']['url'], self.host, rp_session_id, rp_event_id)
        except Exception as e_:
            raise NameError('Config parameter missing or empty, please check config')

        try:
            self.ticket = self._create_rp_ticket(rp_session_id)
        except Exception as e_:
            raise NameError('Could not create ticket')

        if not self.ticket:
            return

        # todo this should in the publish function for better error handling
        # voctoweb: DEACTIVATED here
        if self.ticket.profile_media_enable == 'yes' and self.ticket.media_enable == 'yes':
            api_url = self.config['voctoweb']['api_url']
            api_key = self.config['voctoweb']['api_key']
            self.vw = VoctowebClient(self.ticket, api_key, api_url)

        # YouTube
        if self.ticket.profile_youtube_enable == 'yes' and self.ticket.youtube_enable == 'yes':
            self.yt = YoutubeAPI(self.ticket, self.config)

        # twitter
        if self.ticket.twitter_enable == 'yes':
            self.token = self.config['twitter']['token']
            self.token_secret = self.config['twitter']['token_secret']
            self.consumer_key = self.config['twitter']['consumer_key']
            self.consumer_secret = self.config['twitter']['consumer_secret']

    def publish(self):
        """
        Decide based on the information provided in the ticket where to publish.
        """
        # check source file and filesystem permissions
        if not os.path.isfile(self.ticket.publishing_path + self.ticket.local_filename):
            raise IOError('Source file does not exist (%s)' % (self.ticket.publishing_path + self.ticket.local_filename))
        if not os.path.exists(self.ticket.publishing_path):
            raise IOError("Output path does not exist (%s)" % self.ticket.publishing_path)
        else:
            if not os.access(self.ticket.publishing_path, os.W_OK):
                raise IOError("Output path is not writable (%s)" % self.ticket.publishing_path)

        # Voctoweb: DEACTIVATED
        logging.debug(
            'encoding profile media flag: ' + self.ticket.profile_media_enable + " project media flag: " + self.ticket.media_enable)

        if self.ticket.profile_media_enable == "yes" and self.ticket.media_enable == "yes":
            self._publish_to_voctoweb()

        # YouTube
        logging.debug(
            "encoding profile youtube flag: " + self.ticket.profile_youtube_enable + ' project youtube flag: ' + self.ticket.youtube_enable)

        if self.ticket.profile_youtube_enable == 'yes' and self.ticket.youtube_enable == 'yes' and not self.ticket.has_youtube_url:
            self._publish_to_youtube()

        # Twitter
        if self.ticket.twitter_enable == 'yes':
            twitter.send_tweet(self.ticket, self.token, self.token_secret, self.consumer_key, self.consumer_secret)

        self.rp.set_ticket_done()

    def _get_ticket_from_tracker(self):
        """
        RP17: create our ticket
        """
        logging.info('creating a new ticket')

        #ticket_id = self.rp.assign_next_unassigned_for_state(self.from_state, self.to_state)
        ticket_id = session_id
        if ticket_id:
            logging.info("Ticket ID:" + str(ticket_id))
            tracker_ticket = self.rp.get_ticket_properties()
            logging.debug("Ticket: " + str(tracker_ticket))

            t = Ticket(tracker_ticket, ticket_id)
        else:
            logging.info("No ticket to publish, exiting")
            return None

        return t
    # MOD
    def _get_ticket_from_rp(self):
        """
        Creating a new ticket for processing an rp file
        """
        logging.info('creating a new ticket from rp api')

        ticket_id = self.rp.assign_next_unassigned_for_state(self.from_state, self.to_state)
        if ticket_id:
            logging.info("Ticket ID:" + str(ticket_id))
            tracker_ticket = self.rp.get_ticket_properties()
            logging.debug("Ticket: " + str(tracker_ticket))

            t = Ticket(tracker_ticket, ticket_id)
        else:
            logging.info("No ticket to publish, exiting")
            return None

        return t

    def _publish_to_voctoweb(self):
        """
        Create a event on an voctomix instance. This includes creating a event and a recording for each media file.
        This methods also start the scp uploads and handles multi language audio
        """
        logging.info("publishing to voctoweb")

        if self.ticket.master:
            # if this is master ticket we need to check if we need to create an event on voctoweb
            logging.debug('this is a master ticket')
            if self.ticket.recording_id:
                logging.debug('ticket has a recording id')
                # ticket has an recording id. We assume the event exists on media
                # todo ask media api if event exists
            else:
                # ticket has no recording id therefore we create the event on voctoweb
                r = self.vw.create_event()
                if r.status_code in [200, 201]:
                    logging.info("new event created")
                    # generate the thumbnails (will not overwrite existing thumbs)
                    # todo move the external bash script to python code here
                    # if this is an audio only release we don' create thumbs
                    if self.ticket.mime_type.startswith('video'):
                        if not os.path.isfile(self.ticket.publishing_path + self.ticket.local_filename_base + ".jpg"):
                            self.vw.generate_thumbs()
                            self.vw.upload_thumbs()
                        else:
                            logging.info("thumbs exist. skipping")

                elif r.status_code == 422:
                    # If this happens tracker and voctoweb are out of sync regarding the recording id
                    logging.warning("event already exists => publishing")
                else:
                    raise RuntimeError(("ERROR: Could not add event: " + str(r.status_code) + " " + r.text))

                # in case of a multi language release we create here the single language files
                if len(self.ticket.languages) > 1:
                    logging.info('remuxing multi-language video into single audio files')
                    self._mux_to_single_language()

        # set hq filed based on ticket encoding profile slug
        if 'hd' in self.ticket.profile_slug:
            hq = True
        else:
            hq = False

        # if multi language release we don't want to set the html5 flag for the master
        if len(self.ticket.languages) > 1:
            html5 = False
        else:
            html5 = True

        if self.ticket.mime_type.startswith('audio'):
            # if we have the language index we use it else we assume its 0
            if self.ticket.language_index and len(self.ticket.language_index) > 0:
                index = int(self.ticket.language_index)
            else:
                index = 0
            filename = self.ticket.language_template % self.ticket.languages[index] + '.' + self.ticket.profile_extension
            language = self.ticket.languages[index]
        else:
            filename = self.ticket.filename
            language = self.ticket.language

        self.vw.upload_file(self.ticket.local_filename, filename, self.ticket.folder)

        recording_id = self.vw.create_recording(self.ticket.local_filename, filename,
                                                self.ticket.folder, language, hq, html5)

        self.rp.set_ticket_properties({'Voctoweb.RecordingId.Master': recording_id})

    def _mux_to_single_language(self):
        """
        Mux a multi language video file into multiple single language video files.
        This is only implemented for the h264 hd files as we only do it for them
        :return:
        """
        logging.debug('Languages: ' + str(self.ticket.languages))
        for key in self.ticket.languages:
            out_filename = self.ticket.fahrplan_id + "-" + self.ticket.profile_slug + "-audio" + str(key) + "." + self.ticket.profile_extension
            out_path = os.path.join(self.ticket.publishing_path, out_filename)
            filename = self.ticket.language_template % self.ticket.languages[key] + '.' + self.ticket.profile_extension

            logging.info('remuxing ' + self.ticket.local_filename + ' to ' + out_path)

            try:
                subprocess.call(['ffmpeg', '-y', '-v', 'warning', '-nostdin', '-i',
                                 os.path.join(self.ticket.publishing_path, self.ticket.local_filename), '-map', '0:0',
                                 '-map',
                                 '0:a:' + str(key), '-c', 'copy', '-movflags', 'faststart', out_path])
            except Exception as e_:
                #raise PublisherException('error remuxing ' + self.ticket.local_filename + ' to ' + out_path) from e_
                raise NameError('error remuxing ' + self.ticket.local_filename + ' to ' + out_path)

            try:
                self.vw.upload_file(out_path, filename, self.ticket.folder)
            except Exception as e_:
                #raise PublisherException('error uploading ' + out_path) from e_
                raise NameError('error uploading ' + out_path)

            try:
                self.vw.create_recording(out_filename, filename, self.ticket.folder, str(self.ticket.languages[key]), True, True)
            except Exception as e_:
                #raise PublisherException('creating recording ' + out_path) from e_
                raise NameError('creating recording ' + out_path)
                
    def _publish_to_youtube(self):
        """
        Publish the file to YouTube.
        """
        logging.debug("publishing to youtube")
        youtube_urls = self.yt.publish()
        props = {}
        for i, youtubeUrl in enumerate(youtube_urls):
            props['YouTube.Url' + str(i)] = youtubeUrl

        self.rp.set_ticket_properties(props)


class PublisherException(Exception):
    pass


if __name__ == '__main__':
    try:
        publisher = Publisher()
    except Exception as e:
        logging.error(e)
        logging.exception(e)
        sys.exit(-1)

    if publisher.ticket:
        try:
            publisher.publish()
        except Exception as e:
            publisher.rp.set_ticket_failed(str(e))
            logging.exception(e)
            sys.exit(-1)
    else:
        sys.exit(0)
