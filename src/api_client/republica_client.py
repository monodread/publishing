#    Copyright (C) 2016 derpeter
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

# Are all of these needed?
import xmlrpc.client
import hashlib
import hmac
import socket
import urllib
import xml
import logging
# our old modules used
import urllib2
import argparse
import os
import sys
import subprocess # MOD from subprocess import Popen
import commands
import simplejson as json
import HTMLParser
import textwrap

# the other files
import config
import republica_schedule as schedule
from model.ticket_module import Ticket, TicketException

dry_run = False
#debug = False

h = HTMLParser.HTMLParser()


class RPClient:
    """
    args needed: (self)
    url: where the RP Website API lives
    secret: client secret (unused currently)
    host: client hostname (will be taken from local host if set to None)
    session_id: id for which to look up the data
    event_id= id of the annual republica
    """

    def __init__(self, url, host, session_id, event_id):
        self.url = url + '?args[0]=' + event_id
        #self.group = group
        self.host = host
        #self.secret = secret
        self.ticket_id = session_id
        self.event_id = event_id

    def _create_rp_ticket(self, session_id):
        logging.info("fetching meta data from API, for TalkID "+session_id)
        session = self._get_session_data(session_id, self.event_id)
        # for complete info
        logging.info(json.dumps(event, ensure_ascii=False ,sort_keys=True, indent=4, separators=(',', ': ')))
        # 1: transfer data into ticket
        self.ticket_json = {
        'Fahrplan.Title': session['title'],
        'Fahrplan.Room': session['room'],
        'Fahrplan.ID': session['nid'],
        'Meta.Year': '2016',
        'Fahrplan.GUID': '123456',
        'Fahrplan.Date': session['date'],
        'Fahrplan.Description': session['description'],
        'Processing.Path.Output': '/video/encoded/rel-test/',
        'Publishing.YouTube.EnableProfile': 'yes',
        'Publishing.YouTube.Token': 'FIXME',
        'Publishing.Twitter.Enable': 'no',
        'Publishing.Media.Enable': 'no',
        'Publishing.Media.EnableProfile': 'yes',
        'Publishing.YouTube.Tags': 'test,script,python',
        'Publishing.YouTube.Privacy': 'private FIXME',
        'Processing.Auphonic.Enable': 'no',
        'Publishing.Media.Host': '192.168.23.42',
        'Publishing.Path': '/video/4release/rel-test/',
        'Record.Container': 'TS',
        'EncodingProfile.IsMaster': 'yes',
        'Record.Language.3': 'gsw',
        'Meta.Album': 'Album',
        'Fahrplan.Slug': 'supercon2023',
        'Project.Slug': 'rel-test',
        'EncodingProfile.Basename': 'rel-test-2342-deu-eng-spa-gsw-testi_mc_testface_hd',
        'Publishing.Media.User': 'ubuntu',
        'Processing.Video.AspectRatio': '16:9',
        'Record.Language': 'deu-eng-spa-gsw',
        'EncodingProfile.Extension': 'mp4',
        'Encoding.LanguageIndex': '1',
        'Encoding.Basename': 'rel-test-2342-deu-eng-spa-gsw-testi_mc_testface',
        'Record.Language.1': 'eng',
        'Publishing.Media.Thumbpath': '/tmp/',
        'Publishing.Media.Url': 'https://media.ccc.de/v/fasel',
        'Fahrplan.Subtitle': 'subitdidup',
        'Publishing.Media.Slug': 'supercon2023',
        'EncodingProfile.MirrorFolder': 'h264-hd',
        'Publishing.YouTube.Category': '27',
        'Publishing.Media.Path': '/tmp/',
        'Publishing.YouTube.Enable': 'no',
        'Encoding.LanguageTemplate': 'rel-test-2342-%s-testi_mc_testface',
        'Meta.License': '(C) All rights reserved.',
        'Publishing.Media.MimeType': 'video/mp4',
        'Record.Language.2': 'spa',
        'Processing.Path.Tmp': '/video/tmp/rel-test/',
        'Fahrplan.Abstract': 'lorem und so weiter',
        'EncodingProfile.Slug': 'hd',
        'Record.Language.0': 'deu'
        }
        # 2: initiate the ticket module
        t = Ticket(self.ticket_json, session_id) #args: ticket, ticket_id
        print "Created Ticket for Session: "
        print session['title'].encode('utf-8')
        # return something?

    def _get_session_data(session_id, event_id):
        # fetch individual session
        sessionjsonurl=self.url+'&nid='+session_id
        if config.offline:
            session_tmp = open(session_id+'.json')
        else:
            if debug:
                print sessionjsonurl
            session_tmp = urllib2.urlopen(sessionjsonurl)
        data = json.load(session_tmp, 'utf-8') # format input from json to python dict type
        # pretty-format obj as json str for posting? #DEBUG
        # d2 = json.dumps(data, ensure_ascii=False ,sort_keys=True, indent=4, separators=(',', ': '))
        # print d2
        session_tmp.close()

        if len(data) > 0 and len(data[0]) > 0:
            session = data[0]
            # fix a few things: keep date from datetime
            session['date'] = session['datetime']['value'].split(' ', 1)[0]
            session['time'] = session['datetime']['value'].split(' ', 1)[1]
            print "got session"
        else:
            print "no session data found"
            raise Exception('no sessions with id: ' + session_id)

        return session

    def _get_person_data(person_id, event_id):
        speakerurl='https://re-publica.com/rest/speakers.json?args[0]='+event_id
        if config.offline:
            p_tmp = open('speaker_'+person_id+'.json')  # not currently used?
        else:
            if debug:
                print speakerurl+'&uid='+person_id
            p_tmp = urllib2.urlopen(speakerurl+'&uid='+person_id)
        data = json.load(p_tmp,'utf-8')
        persondata = data[0]
        p2 = json.dumps(data, ensure_ascii=False ,sort_keys=True, indent=4, separators=(',', ': '))
    #     print "\n\n"
    #     print p2
    #     print "\n\n"
        p_tmp.close()
        # add value for a full name
        persondata['name'] = persondata['gn']+' '+persondata['sn']

        return persondata

    def _get_all_sessions(event_id):
        jsonurl=self.url
        if config.offline:
            tmp = open('sessions.json') # not currently used?
        else:
            tmp = urllib2.urlopen(jsonurl)
        data = json.load(tmp, 'utf-8')
        # pretty-format obj as json str for posting? #DEBUG
        # d2 = json.dumps(data, ensure_ascii=False ,sort_keys=True, indent=4, separators=(',', ': '))
        # print d2
        tmp.close()
        return data

    def _get_yt_upload_options(session):
        #session = get_session_data(session_id, event_id)
        # for later concatenation
        title = session['title']
        description = session['description_short']

        # convenience array of speaker names
        persons = session['speaker_names']
        # convenience array of speaker profile user ids
        person_ids = session['speaker_uids']

        # dict used to submit options to youtube (needs to be converted to youtube object, I believe)
        options = dict(session=session['event_title']) # create dict with one entry ('event': 'rpYEAR')
        options['id'] = session['nid']
        # 08.05.2014 - 10:30 bis 11:00 (start and end are also avail)
        options['datetime'] = session['date']+'T'+session['time']

        # I really dislike this heuristic, but I think we'll keep it for now
        if len(persons) == 1 and persons[0]:
            options["title"] = session['event_title'] + ' - ' + persons[0] + ': ' + title
        #elif len(persons) == 2:
        #    options["title"] =  session['event_title'] + ' - ' + persons[0] + ', ' + persons[1] + ': ' + title
        else:
            options["title"] = session['event_title']  + ' - ' + title

        # trim title. this is stupid since we've concatenated a bunch of crap without checking it's length
        # Youtube allows max 100 chars, see https://groups.google.com/d/msg/youtube-api-gdata/RzzD0MxFLL4/YiK83QnS3rcJ
        if len(options["title"]) > 100:
             options["title"] = options["title"][:100] # hard trim
             print 'trimmed title for youtube compatibility!/n'

        # truncated on word boundary
        temp_desc = textwrap.wrap(description, 700)
        description = textwrap.wrap(description, 700)[0]
        # add ... if description was truncated
        if len(temp_desc) > 1:
            description += '...'
            print 'truncated description !!/n'

        options["description"] = '\n\n'. join(filter(None, [
                'Find out more at: ' + session['uri'],
                description
            ]))


        for p in person_ids:
            # ignore empty person entries (was relevant for rp13 xml)
            if not p:
                continue
            person = get_person_data(p, self.event_id)
            wo = person['org_uri']

    #
    #         options["description"] += ('\n\n'
    #           + person['label'] + str(wo and '\n') + str(wo)
    #         )

    # here was Tom Orr's unicode Workaround!!


            #options["description"] += ('\n\n'
            #    + ' | '.join(  [ person['label'] ] + person['link_uris'] )
            #    + str(wo and '\n') + str(wo)
            #)
            #options["description"] += ('\n\n'
            #    + ' | '.join(filter(None, [person[a] for a in ['label', 'website_personal', 'twitter', 'facebook']]))
            #    + str(wo and '\n') + str(wo)

        options["description"] += '\n\nCreative Commons Attribution-ShareAlike 3.0 Germany \n(CC BY-SA 3.0 DE)'

        # this sucks. we should use meta data from the event itself
        keywords = ['#rp'+config.year, 'rp'+config.year, 're:publica', 'republica',
            session["category"], session["room"]] + [p for p in persons]
        options["keywords"] = ', ' . join(keywords)
        options["category"] = session["category"]
        options["subtitle"] = ''

        options["person_labels"] = ', '.join(persons)

        options["slug"] = session['uri'].split('/', 2)[2]

        return options

    # NOT NEEDED?
    def _gen_signature(self, method, args):
        """
        generate signature
        assemble static part of signature arguments
        1. URL  2. method name  3. worker group token  4. hostname
        :param method:
        :param args:
        :return:
        """
        sig_args = urllib.parse.quote(self.url + "&" + method + "&" + self.group + "&" + self.host + "&", "~")

        # add method args
        if len(args) > 0:
            i = 0
            while i < len(args):
                arg = args[i]
                if isinstance(arg, bytes):
                    arg = arg.decode()
                if isinstance(arg, dict):
                    kvs = []
                    for k, v in args[i].items():
                        kvs.append(urllib.parse.quote('[' + str(k) + ']', '~') + '=' + urllib.parse.quote(str(v), '~'))
                    arg = '&'.join(kvs)
                else:
                    arg = urllib.parse.quote(str(arg), '~')

                sig_args = str(sig_args) + str(arg)
                if i < (len(args) - 1):
                    sig_args = sig_args + urllib.parse.quote('&')
                i += 1

        # generate the hmac hash with the key
        hash_ = hmac.new(bytes(self.secret, 'utf-8'), bytes(sig_args, 'utf-8'), hashlib.sha256)
        return hash_.hexdigest()
    # NOT NEEDED?
    def _open_rpc(self, method, args=[]):
        """
        create xmlrpc client
        :param method:
        :param args:
        :return:
        """
        logging.debug('creating XML RPC proxy: ' + self.url + "?group=" + self.group + "&hostname=" + self.host)
        if self.ticket_id:
            args.insert(0, self.ticket_id)

        try:
            proxy = xmlrpc.client.ServerProxy(self.url + "?group=" + self.group + "&hostname=" + self.host)
        except xmlrpc.client.Fault as err:
            msg = "A fault occurred\n"
            msg += "Fault code: %d \n" % err.faultCode
            msg += "Fault string: %s" % err.faultString
            #raise RPException(msg) from err
            raise NameError(msg)

        except xmlrpc.client.ProtocolError as err:
            msg = "A protocol error occurred\n"
            msg += "URL: %s \n" % err.url
            msg += "HTTP/HTTPS headers: %s\n" % err.headers
            msg += "Error code: %d\n" % err.errcode
            msg += "Error message: %s" % err.errmsg
            #raise RPException(msg) from err
            raise NameError(msg)

        except socket.gaierror as err:
            msg = "A socket error occurred\n"
            msg += err
            #raise RPException(msg) from err
            raise NameError(msg)

        args.append(self._gen_signature(method, args))

        try:
            logging.debug(method + str(args))
            result = getattr(proxy, method)(*args)
        except xml.parsers.expat.ExpatError as err:
            msg = "A expat err occured\n"
            msg += err
            #raise RPException(msg) from err
            raise NameError(msg)
        except xmlrpc.client.Fault as err:
            msg = "A fault occurred\n"
            msg += "Fault code: %d\n" % err.faultCode
            msg += "Fault string: %s" % err.faultString
            #raise RPException(msg) from err
            raise NameError(msg)
        except xmlrpc.client.ProtocolError as err:
            msg = "A protocol error occurred\n"
            msg += "URL: %s\n" % err.url
            msg += "HTTP/HTTPS headers: %s\n" % err.headers
            msg += "Error code: %d\n" % err.errcode
            msg += "Error message: %s" % err.errmsg
            #raise RPException(msg) from err
            raise NameError(msg)
        except OSError as err:
            msg = "A OS error occurred\n"
            msg += "Error message: %s" % err
            #raise RPException(msg) from err
            raise NameError(msg)

        return result
    # NOT NEEDED?
    def get_version(self):
        """
        get Tracker Version
        :return:
        """
        return str(self._open_rpc("RP.getVersion"))
    # NOT NEEDED?
    def assign_next_unassigned_for_state(self, from_state, to_state):
        """
        check for new ticket on tracker an get assignment
        :param from_state:
        :param to_state:
        :return:
        """
        ret = self._open_rpc("RP.assignNextUnassignedForState", [from_state, to_state])
        # if we get no xml here there is no ticket for this job
        if not ret:
            return False
        else:
            self.ticket_id = ret['id']
            return ret['id']
    # NOT NEEDED?
    def set_ticket_properties(self, properties):
        """
        set ticket properties
        :param properties:
        :return:
        """
        ret = self._open_rpc("RP.setTicketProperties", [properties])
        if not ret:
            logging.error("no xml in answer")
            return False
        else:
            return True
    # NOT NEEDED?
    def get_ticket_properties(self):
        """
        get ticket properties
        :return:
        """
        ret = self._open_rpc("RP.getTicketProperties")
        if not ret:
            logging.error("no xml in answer")
            return None
        else:
            return ret

    def set_ticket_done(self):
        """
        set Ticket status on done
        :return:
        """
        ret = self._open_rpc("RP.setTicketDone")
        logging.debug(str(ret))

    def set_ticket_failed(self, error):
        """
        set ticket status on failed an supply a error text
        :param error:
        :return:
        """
        self._open_rpc("RP.setTicketFailed", [error.encode('ascii', 'xmlcharrefreplace')])


class RPException(Exception):
    pass
