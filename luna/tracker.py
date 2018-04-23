'''
Written by Dmitry Chirikov <dmitry@chirikov.ru>
This file is part of Luna, cluster provisioning tool
https://github.com/dchirikov/luna

This file is part of Luna.

Luna is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Luna is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Luna.  If not, see <http://www.gnu.org/licenses/>.

'''
#
# Based on Pytt by
# @author: Sreejith K <sreejithemk@gmail.com>
# Created on 12th May 2011
# http://foobarnbaz.com
#

import random
import logging
import binascii
import datetime
import tornado.web
import tornado.gen

from struct import pack
from socket import inet_aton
from httplib import responses
from libtorrent import bencode

import luna


class BaseHandler(tornado.web.RequestHandler):
    """info_hach and peer_id can contain non-unicode symbols"""

    def decode_argument(self, value, name):
        # info_hash is raw_bytes, hexify it.
        if name in ['info_hash', 'peer_id']:
            value = binascii.hexlify(value)

        return super(BaseHandler, self).decode_argument(value, name)


class AnnounceHandler(BaseHandler):
    """Track the torrents. Respond with the peer-list"""

    def initialize(self, params):
        self.PEER_INCREASE_LIMIT = 30
        self.DEFAULT_ALLOWED_PEERS = 50
        self.MAX_ALLOWED_PEERS = 200
        self.INFO_HASH_LEN = 20 * 2  # info_hash is hexified.
        self.PEER_ID_LEN = 20 * 2  # peer_hash is hexified.

        # HTTP Error Codes for BitTorrent Tracker
        self.INVALID_REQUEST_TYPE = 100
        self.MISSING_INFO_HASH = 101
        self.MISSING_PEER_ID = 102
        self.MISSING_PORT = 103
        self.INVALID_INFO_HASH = 150
        self.INVALID_PEER_ID = 151
        self.INVALID_NUMWANT = 152
        self.GENERIC_ERROR = 900
        self.PYTT_RESPONSE_MESSAGES = {
            self.INVALID_REQUEST_TYPE: 'Invalid Request type',
            self.MISSING_INFO_HASH: 'Missing info_hash field',
            self.MISSING_PEER_ID: 'Missing peer_id field',
            self.MISSING_PORT: 'Missing port field',
            self.INVALID_INFO_HASH: ('info_hash is not %d bytes' %
                                     self.INFO_HASH_LEN),
            self.INVALID_PEER_ID: 'peer_id is not %d bytes' % self.PEER_ID_LEN,
            self.INVALID_NUMWANT: ('Peers more than %d is not allowed.' %
                                   self.MAX_ALLOWED_PEERS),
            self.GENERIC_ERROR: 'Error in request',
        }
        responses.update(self.PYTT_RESPONSE_MESSAGES)

        self.tracker_interval = params['luna_tracker_interval']
        self.tracker_min_interval = params['luna_tracker_min_interval']
        self.tracker_maxpeers = params['luna_tracker_maxpeers']
        self.mongo_db = params['mongo_db']

    @tornado.web.asynchronous
    @tornado.gen.engine
    def update_peers(self, info_hash, peer_id, ip, port, status, uploaded,
                     downloaded, left):
        """Store the information about the peer"""

        updated = datetime.datetime.utcnow()
        json = {'peer_id': peer_id, 'updated': updated,
                'uploaded': uploaded, 'downloaded': downloaded, 'left': left}

        if status:
            json['status'] = status

        self.mongo_db['tracker'].find_and_modify({'info_hash': info_hash,
                                                  'ip': ip, 'port': port},
                                                 {'$set': json}, upsert=True)

    @tornado.web.asynchronous
    @tornado.gen.engine
    def get_peers(self, info_hash, numwant, compact, no_peer_id, age):
        time_age = datetime.datetime.utcnow() - datetime.timedelta(seconds=age)
        peer_tuple_list = []
        n_leechers = 0
        n_seeders = 0

        nodes = self.mongo_db['tracker'].find({'info_hash': info_hash,
                                               'updated': {'$gte': time_age}},
                                              {'peer_id': 1, 'ip': 1,
                                               'port': 1, 'status': 1})
        for doc in nodes:
            peer_tuple_list.append((binascii.unhexlify(doc['peer_id']),
                                    doc['ip'], doc['port']))

            try:
                n_leechers += int(doc['status'] == 'started')
                n_seeders += int(doc['status'] == 'completed')
            except:
                pass

        peer_id = binascii.hexlify('lunalunalunalunaluna')
        servers = self.mongo_db['tracker'].find({'info_hash': info_hash,
                                                 'peer_id': peer_id,
                                                 'port': {'$ne': 0}},
                                                {'peer_id': 1, 'ip': 1,
                                                 'port': 1, 'status': 1})
        for doc in servers:
            peer_tuple_list.append((binascii.unhexlify(doc['peer_id']),
                                    doc['ip'], doc['port']))

            try:
                n_leechers += int(doc['status'] == 'started')
                n_seeders += int(doc['status'] == 'completed')
            except:
                pass

        # It's believed it will get better 'cohesion'
        if numwant > len(peer_tuple_list):
            numwant = len(peer_tuple_list)

        peers = []
        compact_peers = b''
        random_peer_list = random.sample(peer_tuple_list, numwant)
        for peer_info in random_peer_list:
            if compact:
                try:
                    ip = inet_aton(peer_info[1])
                    port = pack('>H', int(peer_info[2]))
                    compact_peers += (ip+port)
                except:
                    pass

                continue

            p = {}
            p['peer_id'], p['ip'], p['port'] = peer_info
            peers.append(p)

        self.response['complete'] = n_seeders
        self.response['incomplete'] = n_leechers

        if compact:
            logging.debug('compact peer list: %r' % compact_peers)
            peers = compact_peers
            self.response['peers'] = compact_peers

        else:
            logging.debug('peer list: %r' % peers)
            self.response['peers'] = peers

    @tornado.web.asynchronous
    def get(self):
        failure_reason = ''
        warning_message = ''

        # get all the required parameters from the HTTP request.
        info_hash = self.get_argument('info_hash', default=None)
        if info_hash is None:
            self.send_error(self.MISSING_INFO_HASH)
            return
        elif len(info_hash) != self.INFO_HASH_LEN:
            self.send_error(self.INVALID_INFO_HASH)
            return

        peer_id = self.get_argument('peer_id', default=None)
        if peer_id is None:
            self.send_error(self.MISSING_PEER_ID)
            return
        elif len(peer_id) != self.PEER_ID_LEN:
            self.send_error(self.INVALID_PEER_ID)
            return

        xreal_ip = self.request.headers.get('X-Real-IP', default=None)
        announce_ip = self.get_argument('ip', default=None)

        if announce_ip == '0.0.0.0':
            announce_ip = None

        # can return IP address of the wrong interface. Be careful!
        request_remote_ip = self.request.remote_ip

        ip = announce_ip or xreal_ip or request_remote_ip

        try:
            port = int(self.get_argument('port'))
        except:
            self.send_error(self.MISSING_PORT)
            return

        info_hash = str(info_hash)
        uploaded = int(self.get_argument('uploaded', default=0))
        downloaded = int(self.get_argument('downloaded', default=0))
        left = int(self.get_argument('left', default=0))
        compact = int(self.get_argument('compact', default=0))
        no_peer_id = int(self.get_argument('no_peer_id', default=0))
        event = self.get_argument('event', default='')
        tracker_id = self.get_argument('trackerid', default='')

        numwant = int(self.get_argument('numwant',
                                        default=self.DEFAULT_ALLOWED_PEERS))

        if numwant > self.tracker_maxpeers:
            # XXX: cannot request more than MAX_ALLOWED_PEERS.
            self.send_error(self.INVALID_NUMWANT)
            return

        self.update_peers(info_hash, peer_id, ip, port, event,
                          uploaded, downloaded, left)

        # generate response
        self.response = {}

        # Interval in seconds that the client should wait between sending
        # regular requests to the tracker.
        self.response['interval'] = self.tracker_interval

        # Minimum announce interval. If present clients must not re-announce
        # more frequently than this.
        self.response['min interval'] = self.tracker_min_interval

        self.response['tracker id'] = tracker_id

        if failure_reason:
            self.response['failure reason'] = failure_reason

        if warning_message:
            self.response['warning message'] = warning_message

        self.get_peers(info_hash, numwant, compact, no_peer_id,
                       self.tracker_interval * 2)

        self.set_header('Content-Type', 'text/plain')
        self.write(bencode(self.response))
        self.finish()


class ScrapeHandler(AnnounceHandler):
    """Returns the state of all torrents this tracker is managing"""

    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        response = {}

        info_hashes = self.get_arguments('info_hash')
        for info_hash in info_hashes:
            info_hash = str(info_hash)
            response[info_hash] = {}
            numwant = 100
            compact = True
            no_peer_id = 1

            complete, incomplete, _ = self.get_peers(info_hash, numwant,
                                                     compact, no_peer_id,
                                                     self.tracker_interval * 2)

            response[info_hash]['complete'] = complete
            response[info_hash]['downloaded'] = complete
            response[info_hash]['incomplete'] = incomplete

        self.set_header('content-type', 'text/plain')
        self.write(bencode(response))
        self.finish()
