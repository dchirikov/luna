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

from config import usedby_key, db_name, db_version

import os
import pwd
import grp
import errno
import base64
import logging
import subprocess

from bson.objectid import ObjectId
from tornado import template
from pymongo.errors import OperationFailure

from luna.base import Base
from luna import utils


class Cluster(Base):
    """
    Class for storing options and procedures for luna
    TODO rename to 'Cluster'
    """

    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger(__name__)
    _mongo_collection = None
    _keylist = None
    _id = None
    _name = None
    _DBRef = None
    _json = None

    def __init__(self, mongo_db=None, create=False, id=None,
                 nodeprefix='node', nodedigits=3, path=None, user=None):
        """
        Constructor can be used for creating object by setting create=True
        nodeprefix='node' and nodedigits='3' will give names like node001,
        nodeprefix='compute' and nodedigits='2' will give names like compute01
        """

        self.log.debug("function args {}".format(self._debug_function()))

        self._collection_name = 'cluster'
        self._keylist = {'nodeprefix': type(''),
                         'nodedigits': type(0),
                         'debug': type(0),
                         'user': type(''),
                         'path': type(''),
                         'frontend_address': type(''),
                         'frontend_port': type(0),
                         'server_port': type(0),
                         'tracker_interval': type(0),
                         'tracker_min_interval': type(0),
                         'tracker_maxpeers': type(0),
                         'torrent_listen_port_min': type(0),
                         'torrent_listen_port_max': type(0),
                         'torrent_pidfile': type(''),
                         'lweb_pidfile': type(''),
                         'lweb_num_proc': type(0),
                         'cluster_ips': type(''),
                         'named_include_file': type(''),
                         'named_zone_dir': type(''),
                         'dhcp_range_start': long,
                         'dhcp_range_end': long,
                         'dhcp_net': type(''),
                         'comment': type(''),
                         'frontend_https': type(True)}

        cluster = self._get_object('general', mongo_db, create, id)

        if cluster and cluster.get('db_version') != db_version:
            err_msg = "DB version mismatch. Expecting {}".format(db_version)
            self.log.error(err_msg)
            raise RuntimeError, err_msg

        if create:
            try:
                path = os.path.abspath(path)
            except:
                err_msg = "No path specified."
                self._logger.error(err_msg)
                raise RuntimeError, err_msg
            if not os.path.exists(path):
                err_msg = "Wrong path '{}' specified.".format(path)
                self._logger.error(err_msg)
                raise RuntimeError, err_msg

            try:
                user_id = pwd.getpwnam(user)
            except KeyError:
                err_msg = "No such user '{}' exists.".format(user)
                self.log.error(err_msg)
                raise RuntimeError, err_msg

            try:
                group = grp.getgrgid(user_id.pw_gid).gr_name
                group_id = grp.getgrnam(group)
            except KeyError:
                err_msg = "No such group '{}' exists.".format(group)
                self.log.error(err_msg)
                raise RuntimeError, err_msg

            path_stat = os.stat(path)

            if (path_stat.st_uid != user_id.pw_uid or
                    path_stat.st_gid != group_id.gr_gid):

                err_msg = "Path is not owned by '{}:{}'".format(user, group)
                self.log.error(err_msg)
                raise RuntimeError, err_msg

            cluster = {'name': 'general',
                       'nodeprefix': nodeprefix,
                       'nodedigits': nodedigits,
                       'user': user, 'debug': 0,
                       'path': path,
                       'cluster_ips': None,
                       'frontend_address': '',
                       'frontend_port': '7050',
                       'server_port': 7051,
                       'torrent_listen_port_min': 7052,
                       'torrent_listen_port_max': 7200,
                       'torrent_pidfile': '/run/luna/ltorrent.pid',
                       'tracker_interval': 10,
                       'tracker_min_interval': 5,
                       'tracker_maxpeers': 200,
                       'lweb_num_proc': 0,
                       'lweb_pidfile': '/run/luna/lweb.pid',
                       'named_include_file': '/etc/named.luna.zones',
                       'named_zone_dir': '/var/named',
                       'dhcp_range_start': None,
                       'dhcp_range_end': None,
                       'dhcp_net': None,
                       'db_version': db_version,
                       'comment': None,
                       'frontend_https': False,
                       }

            self.log.debug("Saving cluster '{}' to the datastore"
                           .format(cluster))

            self.store(cluster)

            try:
                logdir = os.environ['LUNA_LOGDIR']
            except KeyError:
                logdir = '/var/log/luna'

            try:
                os.makedirs(logdir)
            except OSError as exc:
                if exc.errno == errno.EEXIST and os.path.isdir(logdir):
                    pass
                else:
                    raise

            os.chown(logdir, user_id.pw_uid, group_id.gr_gid)

    def get(self, key):
        from luna.network import Network

        if key == 'dhcp_net':
            netid = super(Cluster, self).get(key)
            if not netid:
                return None

            net = Network(id=ObjectId(netid), mongo_db=self._mongo_db)
            try:
                net = Network(id=ObjectId(netid), mongo_db=self._mongo_db)
                return net.name
            except:
                self.log.error('Wrong DHCP network configured')
                return None

        if key == 'dhcp_range_start' or key == 'dhcp_range_end':
            netid = super(Cluster, self).get('dhcp_net')
            if not netid:
                return None

            net = Network(id=ObjectId(netid), mongo_db=self._mongo_db)
            return utils.ip.reltoa(net._json['NETWORK'],
                                   super(Cluster, self).get(key),
                                   ver=net.version)

        return super(Cluster, self).get(key)

    def set(self, key, value):
        if key == 'path':
            try:
                value = os.path.abspath(value)
            except:
                self.log.error("No path specified.")
                return False
            if not os.path.exists(value):
                self.log.error("Wrong path specified.")
                return False

        elif key in ['server_address', 'tracker_address']:
            try:
                utils.ip.aton(value)
            except:
                self.log.error("Wrong ip address specified.")
                return False

        elif key == 'user':
            try:
                pwd.getpwnam(value)
            except:
                self.log.error("No such user exists.")
                return False

        elif key == 'cluster_ips':
            if not bool(value):
                value = ''
            else:
                val = ''
                for ip in value.split(","):
                    try:
                        utils.ip.aton(ip.strip())
                        val += ip + ','
                    except:
                        self.log.error("Wrong ip address specified.")
                        return False

                value = val[:-1]

        return super(Cluster, self).set(key, value)

    def makedhcp_config(self, net_name=None, start_ip=None, end_ip=None):

        from luna.network import Network

        if net_name and not (start_ip and end_ip):
            self.log.error("IP range should be specified.")
            return {}

        old_net_name = self.get('dhcp_net')

        if not (old_net_name or net_name):
            self.log.error("DHCP network should be specified.")
            return {}

        frontend_address = self.get('frontend_address')
        if not frontend_address:
            self.log.error("Frontend address should be set.")
            return {}

        net_obj = None
        start_ip_num, end_ip_num = None, None

        if net_name:
            net_obj = Network(name=net_name, mongo_db=self._mongo_db)

            if net_obj.version != 4:
                self.log.error("Only IPv4 networks are supported.")
                return {}

            start_ip_num = None
            frontend_address_num = None
            end_ip_num = None
            try:
                start_ip_num = utils.ip.atorel(
                    start_ip, net_obj._json['NETWORK'],
                    net_obj._json['PREFIX'])

                frontend_address_num = utils.ip.atorel(
                    frontend_address, net_obj._json['NETWORK'],
                    net_obj._json['PREFIX'])

                end_ip_num = utils.ip.atorel(
                    end_ip, net_obj._json['NETWORK'],
                    net_obj._json['PREFIX'])

            except RuntimeError:
                # utils.ip will print error messages
                pass

            if not start_ip_num:
                self.log.error(
                    'Start of the range does not belong to network.')
                return {}

            if not start_ip_num:
                self.log.error(
                    'End of the range does not belong to network.')
                return {}

            if not frontend_address_num:
                self.log.error(
                    'Frontend IP does not belong to network.')
                return {}

            if end_ip_num < start_ip_num:
                self.log.error(
                    'End IP of the range should be larger than start.')
                return {}

        old_net_obj = None
        old_start_ip = None
        old_end_ip = None

        if old_net_name and net_name:
            # release old range
            old_net_obj = Network(name=old_net_name, mongo_db=self._mongo_db)
            old_start_ip = self.get('dhcp_range_start')
            old_end_ip = self.get('dhcp_range_end')

            res = old_net_obj.release_ip(old_start_ip, old_end_ip)

            if not res:
                self.log.error('Unable to release old range.')
                return {}

            self.unlink(old_net_obj)

        if net_name:
            # now try to reserve new range
            net_obj = Network(name=net_name, mongo_db=self._mongo_db)
            res = net_obj.reserve_ip(start_ip_num, end_ip_num)
            if not res:
                if old_net_obj:
                    # need to rolback
                    old_net_obj.reserve_ip(old_start_ip, old_end_ip)
                self.log.error('Unable to reserve new range.')
                return {}

            super(Cluster, self).set('dhcp_net', str(net_obj.id))
            super(Cluster, self).set('dhcp_range_start', start_ip_num)
            super(Cluster, self).set('dhcp_range_end', end_ip_num)
            self.link(net_obj)

        # get actual options
        c = {}

        if self.get('frontend_https'):
            c['protocol'] = 'https'
        else:
            c['protocol'] = 'http'

        c['frontend_ip'] = self.get('frontend_address')
        c['dhcp_start'] = self.get('dhcp_range_start')
        c['dhcp_end'] = self.get('dhcp_range_end')
        c['frontend_port'] = self.get('frontend_port')
        netname = self.get('dhcp_net')
        objnet = Network(name=netname, mongo_db=self._mongo_db)
        c['netmask'] = objnet.get('NETMASK')
        c['network'] = objnet.get('NETWORK')

        c['hmac_key'] = str(
            base64.b64encode(bytearray(os.urandom(32))).decode()
        )

        c['reservations'] = objnet.get_ip_macs()

        return c

    def makedhcp(self, net_name=None, start_ip=None, end_ip=None, no_ha=False):

        ask_ha = not no_ha

        c = self.makedhcp_config(net_name, start_ip, end_ip)
        if not c:
            self.log.error('Unable to create DHCP config')
            return False

        conf_primary = {}
        conf_secondary = {}

        tloader = template.Loader(self.get('path') + '/templates')

        if self.is_ha() and ask_ha:

            # native dhcp config

            cluster_ips = self.get_cluster_ips()
            conf_primary['my_addr'] = cluster_ips[0]
            conf_secondary['my_addr'] = cluster_ips[1]
            conf_primary['peer_addr'] = conf_secondary['my_addr']
            conf_secondary['peer_addr'] = conf_primary['my_addr']

            dhcpd_conf_primary = tloader.load('templ_dhcpd.cfg').generate(
                c=c, conf_primary=conf_primary,
                conf_secondary=None)

            dhcpd_conf_secondary = tloader.load('templ_dhcpd.cfg').generate(
                c=c, conf_primary=None,
                conf_secondary=conf_secondary)

            f1 = open('/etc/dhcp/dhcpd.conf', 'w')
            f1.write(dhcpd_conf_primary)
            f1.close()

            f2 = open('/etc/dhcp/dhcpd-secondary.conf', 'w')
            f2.write(dhcpd_conf_secondary)
            f2.close()

            return True

        dhcpd_conf = tloader.load('templ_dhcpd.cfg').generate(
            c=c, conf_primary=None, conf_secondary=None)

        f1 = open('/etc/dhcp/dhcpd.conf', 'w')
        f1.write(dhcpd_conf)
        f1.close()

        if self.is_ha():
            # dhcpd-secondary.conf is just a copy of dhcpd.conf
            f2 = open('/etc/dhcp/dhcpd-secondary.conf', 'w')
            f2.write(dhcpd_conf)
            f2.close()

        return True

    def get_cluster_ips(self):
        cluster_ips = []
        ips = self.get('cluster_ips')

        if ips == '':
            self.log.debug('No cluster IPs are configured.')
            return cluster_ips

        ips = ips.split(",")

        local_ip = ''
        for ip in ips:
            stdout = subprocess.Popen(['/usr/sbin/ip', 'addr',
                                       'show', 'to', ip],
                                      stdout=subprocess.PIPE).stdout.read()
            if not stdout == '':
                local_ip = ip
                break

        if not local_ip:
            self.log.info('No proper cluster IPs are configured.')
            return cluster_ips

        cluster_ips.append(local_ip)
        for ip in ips:
            if not ip == local_ip:
                cluster_ips.append(ip)

        return cluster_ips

    def is_active(self):
        cluster_ips = self.get('cluster_ips')

        if not cluster_ips:
            return True

        ip = self.get('frontend_address')
        if not ip:
            return True

        stdout = subprocess.Popen(['/usr/sbin/ip', 'addr',
                                   'show', 'to', ip],
                                  stdout=subprocess.PIPE).stdout.read()
        if stdout:
            return True

        return False

    def is_ha(self):
        try:
            cluster_ips = self.get('cluster_ips')
        except:
            return False

        if cluster_ips:
            return True
        return False

    def makedns(self):
        from luna.network import Network

        # figure out paths
        includefile = self.get('named_include_file')
        zonedir = self.get('named_zone_dir')

        if not includefile:
            self.log.error("named_include_file should be configured")
            return False
        if not zonedir:
            self.log.error("named_zone_dir should be configured")
            return False

        rlinks = self.get(usedby_key)
        if not rlinks or 'network' not in rlinks or not rlinks['network']:
            self.log.error("No networks configured in this cluster")
            return False

        netids = []
        for netid in rlinks['network']:
            netids.append(netid)

        zone_data = {
            4: {'direct': {}, 'reverse': {}},
            6: {'direct': {}, 'reverse': {}}
        }
        serial_num = 1

        for netid in netids:
            netobj = Network(id=ObjectId(netid))
            self.log.debug('Network {}'. format(netobj.name))
            net_zone_data = netobj.zone_data
            self.log.debug('net_zone_data: {}'.format(zone_data))
            rev_zone_name = net_zone_data.pop('rev_zone_name')
            rev_zone_hosts = net_zone_data.pop('rev_hosts')
            include = net_zone_data['include']
            rev_include = net_zone_data['rev_include']
            direct_name = net_zone_data.pop('zone_name')
            version = net_zone_data.pop('version')
            ns_hostname = net_zone_data.pop('ns_hostname')
            ns_hostname += '.' + direct_name

            # It 10.1.0.0/16 and 10.1.128.0/18 will give
            # the same reverse zone 1.10.in-addr.arpa
            # so we need to combine to the single one

            if rev_zone_name in zone_data[version]['reverse']:

                old_rev_zone = zone_data[version]['reverse'][rev_zone_name]
                old_rev_hosts = old_rev_zone['hosts'].copy()

                for rev_host in rev_zone_hosts:
                    if rev_host in old_rev_hosts:
                        self.log.error(
                            "Duplicate records for {}.{}.*.arpa: {} and {}"
                            .format(
                                rev_host,
                                rev_zone_name,
                                old_rev_hosts[rev_host],
                                rev_zone_hosts[rev_host],
                            )
                        )
                    old_rev_hosts[rev_host] = rev_zone_hosts[rev_host]

                (zone_data[version]
                          ['reverse']
                          [rev_zone_name]
                          ['include']) += rev_include

                (zone_data[version]
                          ['reverse']
                          [rev_zone_name]
                          ['hosts']) = old_rev_hosts

            if rev_zone_name not in zone_data[version]['reverse']:
                rev_zone_dict = {
                    'hosts': rev_zone_hosts,
                    'ns_hostname': ns_hostname,
                    'serial': serial_num,
                    'include': rev_include,
                }
                zone_data[version]['reverse'][rev_zone_name] = rev_zone_dict

            direct_zone_dict = {
                'hosts': net_zone_data['hosts'].copy(),
                'ns_ip': net_zone_data['ns_ip'],
                'ns_hostname': ns_hostname,
                'serial': serial_num,
                'include': include,
            }
            zone_data[version]['direct'][direct_name] = direct_zone_dict

        self.log.debug('zone_data: {}'.format(zone_data))

        zones = []
        fsuffix = '.luna.zone'

        for name4 in zone_data[4]['direct']:
            zone = {}
            zone['template'] = 'templ_zone_ipv4.cfg'
            zone['name'] = name4
            zone['file'] = zone['name'] + fsuffix
            zone['data'] = zone_data[4]['direct'][name4]
            zones.append(zone)

        for name6 in zone_data[6]['direct']:
            zone = {}
            zone['template'] = 'templ_zone_ipv6.cfg'
            zone['name'] = name6
            zone['file'] = zone['name'] + fsuffix
            zone['data'] = zone_data[6]['direct'][name6]
            zones.append(zone)

        for rev_name4 in zone_data[4]['reverse']:
            zone = {}
            zone['template'] = 'templ_zone_ipv4_arpa.cfg'
            zone['name'] = rev_name4 + '.in-addr.arpa'
            zone['file'] = zone['name'] + fsuffix
            zone['data'] = zone_data[4]['reverse'][rev_name4]
            zones.append(zone)

        for rev_name6 in zone_data[6]['reverse']:
            zone = {}
            zone['template'] = 'templ_zone_ipv6_arpa.cfg'
            zone['name'] = rev_name6 + '.ip6.arpa'
            zone['file'] = zone['name'] + fsuffix
            zone['data'] = zone_data[6]['reverse'][rev_name6]
            zones.append(zone)

        tloader = template.Loader(self.get('path') + '/templates',
                                  autoescape=None)

        # create include file for named.conf
        namedconffile = open(includefile, 'w')

        namedconffile.write(
            tloader.load('templ_named_conf.cfg').generate(z=zones)
        )

        namedconffile.close()

        nameduid, namedgid = None, None

        try:
            namedgid = grp.getgrnam("named").gr_gid
        except KeyError:
            self.log.error("Unable to find group 'named'")

        try:
            nameduid = pwd.getpwnam("named").pw_uid
        except KeyError:
            self.log.error("Unable to find user 'named'")

        if namedgid:
            os.chown(includefile, 0, namedgid)
        else:
            self.log.error('Unable to set group for {}'.format(includefile))

        self.log.info("Created '{}'".format(includefile))

        # remove zone files
        filelist = [f for f in os.listdir(zonedir) if f.endswith(fsuffix)]
        for f in filelist:
            filepath = zonedir + "/" + f
            try:
                os.remove(filepath)
                self.log.info("Removed old '{}'".format(filepath))
            except:
                self.log.info("Unable to remove '{}'".format(filepath))

        for zone in zones:
            zonefilepath = zonedir + "/" + zone['file']

            with open(zonefilepath, 'w') as zonefile:
                zonefile.write(
                    tloader.load(zone['template']).generate(z=zone['data'])
                )

            if nameduid and namedgid:
                os.chown(zonefilepath, nameduid, namedgid)
            else:
                self.log.error('Unable to set ownership for {}'
                    .format(zone['file'])
                )

            self.log.info("Created '{}'".format(zonefilepath))

        return True

    def delete(self, force=False):

        if force:
            # this will return None
            self._mongo_db.connection.drop_database(db_name)
            try:
                if db_name in self._mongo_db.connection.database_names():
                    self.log.error('Unable to delete DB \'{}\''.format(db_name))
                    return False
            except OperationFailure:
                return True
            return True

        return super(Cluster, self).delete()

    def list_cached_macs(self):
        from luna.switch import Switch
        from luna.node import Node
        cached_macs = utils.helpers.list_cached_macs(mongo_db=self._mongo_db)

        rlinks = self.get(usedby_key)
        if not rlinks or 'switch' not in rlinks or not rlinks['switch']:
            self.log.error("No switches configured in this cluster")
            return False

        switchids = {}
        switchnames = {}
        for switchid in rlinks['switch']:
            sw = Switch(id=ObjectId(switchid), mongo_db=self._mongo_db)
            switchids[switchid] = sw.name
            switchnames[sw.name] = switchid

        nodeids_macs = utils.helpers.list_node_macs(mongo_db=self._mongo_db)
        macs_nodenames = {}

        for nodeid in nodeids_macs:
            node = Node(id=ObjectId(nodeid), mongo_db=self._mongo_db)
            macs_nodenames[nodeids_macs[nodeid]] = {
                'name': node.name,
                'switch_id': node.get('switch'),
                'port': node.get('port'),
            }

        swlist = switchnames.keys()
        swlist.sort()

        for i in range(len(cached_macs)):
            swid = str(cached_macs[i]['switch_id'])
            cached_macs[i]['switch'] = switchids[swid]
            if cached_macs[i]['mac'] in macs_nodenames:
                node = macs_nodenames[cached_macs[i]['mac']]
                nodename = node['name']

                if ((cached_macs[i]['port'] == node['port'] or
                        cached_macs[i]['portname'] == node['port']) and
                        node['switch_id'] and
                        cached_macs[i]['switch_id'] == node['switch_id'].id):
                    cached_macs[i]['configured'] = True
                else:
                    cached_macs[i]['configured'] = False

                cached_macs[i]['node'] = nodename
            else:
                cached_macs[i]['node'] = None
                cached_macs[i]['configured'] = False
            cached_macs[i].pop('_id')
            cached_macs[i].pop('switch_id')
            cached_macs[i].pop('updated')

        res = sorted(
            cached_macs,
            key=lambda x: (x['switch'],
                           int(x['port']),
                           x['portname'],
                           x['mac'],
                           x['node'],
                           )
        )

        return res
