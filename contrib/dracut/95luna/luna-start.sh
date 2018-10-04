#!/bin/bash

# Written by Dmitry Chirikov <dmitry@chirikov.ru>
# This file is part of Luna, cluster provisioning tool
# https://github.com/dchirikov/luna

# This file is part of Luna.

# Luna is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Luna is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Luna.  If not, see <http://www.gnu.org/licenses/>.

echo "Welcome to Luna Installer"
. /lib/dracut-lib.sh

function are_macs_equal () {
    awk -v mac=$1 -v reqmac=$2 'BEGIN{
        if (length(mac) == 17) {
            if (mac == reqmac) {
                print 1
            } else {
                print 0
            }
        } else {
            mac_len = split(mac, mac_array, ":")
            reqmac_len = split(reqmac, reqmac_array, ":")
            j=reqmac_len
            for (i=mac_len; i>0; i--) {
                if ((j>0) && (mac_array[i] == reqmac_array[j])) {
                    j--
                }
            }
            if (j==0) {
                print 1
            } else {
                print 0
            }
        }

    }'
}

function run_dhcpclient() {
    . /lib/dracut-lib.sh
    . /lib/net-lib.sh
    /usr/sbin/dhclient -lf /luna/dhclient.leases
    . $hookdir/initqueue/setup_net_*.sh
    rm -f /tmp/net.*.did-setup
}

function find_nic () {
    REQMAC=$1
    for NIC in /sys/class/net/*; do
        IFNAME=$(basename ${NIC})
        if [ "x${IFNAME}" = "xlo" ]; then
            continue
        fi
        MAC=$(cat ${NIC}/address)
        if [ "$(are_macs_equal $MAC $REQMAC)" -eq 1 ]; then
            echo ${IFNAME}
            break
        fi
    done
}

function luna_start () {
    local luna_ip
    local luna_bootproto
    local luna_mac
    echo "$(getargs luna.hostname=)" > /proc/sys/kernel/hostname
    echo "Luna: Starting ssh"
    echo "sshd:x:74:74:Privilege-separated SSH:/var/empty/sshd:/sbin/nologin" >> /etc/passwd
    echo sshd:x:74: >> /etc/group
    mkdir -p /var/empty/sshd
    /usr/sbin/sshd > /dev/null 2>&1
    echo "Luna: Start shell on tty2"
    luna_ctty2=/dev/tty2
    setsid -c /bin/sh -i -l 0<>$luna_ctty2 1<>$luna_ctty2 2<>$luna_ctty2 &
    udevadm settle
    # settle is not really reliable
    sleep 5
    echo "Luna: Set-up network"
    luna_bootproto=$(getargs luna.bootproto=)
    if [ "x$luna_bootproto" = "xdhcp" ]; then
        echo "Luna: Configuring dhcp for all interfaces"
        run_dhcpclient
    else
        luna_ip=$(getargs luna.ip=)
        luna_mac=$(getargs luna.mac=)
        echo "Luna: ${luna_ip} for interface with mac ${luna_mac} was specified"
        echo "Luna: Trying to find interface for ${luna_mac}"
        luna_nic=$(find_nic ${luna_mac})
        if [ "x${luna_nic}" = "x" ]; then
            echo "Luna: unable to find NIC for mac ${luna_mac}. Starting dhcp"
            run_dhcpclient
        else
            echo "${luna_nic}" > /luna/luna_nic
            export LUNA_BOOTIF="${luna_nic}"
            ip a add ${luna_ip} dev ${luna_nic}
            sleep 1
            ip l set dev ${luna_nic} up
        fi
    fi
}

function luna_finish () {
    # shutdown sshd
    /usr/bin/ps h --ppid `cat /var/run/sshd.pid` -o 'pid' | while read pid; do kill $pid; done
    kill `cat /var/run/sshd.pid`
    # shutdown dhclient
    /usr/sbin/dhclient -lf /luna/dhclient.leases -x
    # bring interfaces down
    if [ -f /luna/luna_nic ]; then
        luna_nic=$(cat /luna/luna_nic)
        ip addr flush ${luna_nic}
        ip link set dev ${luna_nic} down
    else
        cat /luna/dhclient.leases  | \
            sed -n '/interface /s/\W*interface "\(.*\)";/\1/p' | \
            while read iface; do
                ip addr flush $iface
                ip link set dev $iface down
            done
    fi
    # kill shell on tty2
    ps h t tty2 o pid | while read pid; do kill -9 $pid; done

}
function _get_luna_ctty () {
    local luna_ctty
    luna_ctty=$(getargs luna.ctty=)
    # TODO [ "x${luna_ctty}" = "x" ] && luna_ctty=$(getargs console=)
    [ "x${luna_ctty}" = "x" ] && luna_ctty="/dev/tty1"
    echo -n $luna_ctty
}
if [ "x$root" = "xluna" ]; then
    luna_start
    luna_ctty=$(_get_luna_ctty)
    luna_url=$(getargs luna.url=)
    luna_node=$(getargs luna.node=)
    luna_service=$(getargs luna.service=)
    if [ "x$luna_service" = "x1" ]; then
        echo "Luna: Entering Service mode."
        setsid -c /bin/sh -i -l 0<>$luna_ctty 1<>$luna_ctty 2<>$luna_ctty
    else
        RES="failure"
        while [ "x$RES" = "xfailure" ]; do
            echo "Luna: Trying to get install script."
            while ! curl -f -s -m 60 --connect-timeout 10 "$luna_url?step=install&node=$luna_node" > /luna/install.sh; do
                echo "Luna: Could not get install script. Sleeping 10 sec."
                sleep 10
            done
            /bin/sh /luna/install.sh && RES="success"
            echo "Luna: install.sh exit status: $RES"
            sleep 10
        done
    fi
    luna_finish
    echo 'Exit from Luna Installer'
fi
