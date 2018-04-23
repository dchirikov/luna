# Group basics

Groups in luna is a central place where user can define shared attributes for nodes.

# Creating group

To create group 2 other items are mandatory: osimage and network. Logic behind is that make no sence to have nodes without OS and disconnected from network, as Luna is network provisioning tool

```
# luna network list
+------------+------------------+
| Name       | Network          |
+------------+------------------+
| cluster    | 10.141.0.0/16    |
| ipmi       | 10.149.0.0/16    |
+------------+------------------+

# luna osimage list
+------------------+-------------------------------+------------------------------+
| Name             | Path                          | Kernel version               |
+------------------+-------------------------------+------------------------------+
| compute-image    | /opt/luna/os/compute-image    | 3.10.0-693.5.2.el7.x86_64    |
+------------------+-------------------------------+------------------------------+

# luna group add -n compute -o compute-image -N cluster

# luna group show compute
+---------------+-------------------------------------------------+
| Parameter     | Value                                           |
+---------------+-------------------------------------------------+
| name          | compute                                         |
| bmcsetup      | -                                               |
| domain        | [cluster]                                       |
| interfaces    | [BOOTIF]:[cluster]:10.141.0.0/16                |
| osimage       | [compute-image]                                 |
| partscript    | mount -t tmpfs tmpfs /sysroot                   |
| postscript    | cat << EOF >> /sysroot/etc/fstab                |
|               | tmpfs   /       tmpfs    defaults        0 0    |
|               | EOF                                             |
| prescript     |                                                 |
| torrent_if    | -                                               |
| comment       |                                                 |
+---------------+-------------------------------------------------+
```

Please note 2 important things here. First domain option is filled automatically. So hostnames will contain domain part, as 'hode001.cluster'
You are free you change it:
```
# luna group change compute -d ''
```

Second thing that nodes, by default will configured to use ramdisk, so you can boot the node and it won't affect content of the connected disks (if any). You can leave it as is. Or add part and post scripts. See man luna for example scripts.

# Group interfaces

By default group create interface called BOOTIF. This interface is considered the one node is connected to network and Luna dracut module will try to identify it based on MAC address during install. Another special name is BMC - this is the interface of management module (BMC, iLO, iDRAC, etc.). For BMC interface only IPv4 is supported and IPv6 settings will be ignored.

User can also configure additional interfaces.

```
# luna group change compute -i bridge0 -A
# luna group change compute -i bridge0 --setnet cluster
# luna group change compute -i bond0 -A
# luna group change compute -i eth0 -A
# luna group change compute -i eth1 -A

# cat << EOF | luna group change compute -i eth0 -e
SLAVE=yes
MASTER=bond0
ONBOOT=no
EOF

# cat << EOF | luna group change compute -i eth1 -e
SLAVE=yes
MASTER=bond0
ONBOOT=no
EOF

# cat << EOF | luna group change compute -i bond0 -e
BONDING_MASTER=yes
BOOTPROTO=none
ONBOOT=yes
BONDING_OPTS="mode=1"
BRIDGE=bridge0
EOF

# cat << EOF | luna group change compute -i bridge0 -e
TYPE=Bridge
EOF
```
In this config we created bond out of eth0 and eth1 and plug it to network bridge which can be used for creating VMs later.
The same way additional properties of the interaface can be configured: MTU, ZONE, etc.

