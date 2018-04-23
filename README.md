# Disclaimer

Luna is a baremetal provisioning tool that uses an image based approach. It delivers full images of operating systems and not a 'recipe' on how to configure one.
It also dramatically speeds up installation time, and reduces administrative efforts.

# Overview

Luna uses the BitTorrent protocol to provision nodes. As such, every booting node helps the others to boot.

Once a node is fully booted it stops being a torrent seeder and other nodes can no longer use it to download the image. The torrent client only acts in the initrd environment.

Luna does not require any additional services to run on a node. By default it changes very a limited number of files on provisioned nodes.
It us usually limited to `/etc/hostname` and `/etc/sysconfig/network-scripts/ifcfg-*` files.

|Number of nodes|Time for cold boot, min|xCAT cold boot, min|
|:-------------:|:---------------------:|:-----------------:|
|              1|                      3|                  9|
|             36|                      4|                 26|
|             72|                      4|                 53|

Image size is 1GB. Provisioning node is equiped with a 1Gb ethernet interface.

In a cluster of 300 nodes. Boot time using luna has been measured to be aproximately 5 minutes. This includes BIOS POST procedures and all starting systemd services.

# Getting started

Let's assume you have a server using the IP address `10.30.255.254` to provision the cluster

## Server preparation

### Build RPM
```
yum -y install https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
yum -y install wget python-docutils gcc-c++ rb_libtorrent-devel boost-devel make rpm-build redhat-rpm-config
git clone https://github.com/clustervision/luna
cd luna
make rpm
```

Note. Instead of building luna from scratch you can easily configure repository and install everything from it:

```
curl https://updates.clustervision.com/luna/1.2/centos/luna-1.2.repo > /etc/yum.repos.d/luna-1.2.repo
yum install luna
```
### Install hostlist
Source code is available [here](https://www.nsc.liu.se/~kent/python-hostlist/)
```
wget https://www.nsc.liu.se/~kent/python-hostlist/python-hostlist-1.17.tar.gz
rpmbuild -ta python-hostlist-1.17.tar.gz
yum -y install python-hostlist-1.17-1.noarch.rpm
```
### Install Luna
```
yum -y install rpm/RPMS/x86_64/luna-[0-9]*rpm
```

### Configure DB credentials

```
vim /etc/luna.conf
```

### Setup environment

```
[ -f /root/.ssh/id_rsa ] || ssh-keygen -t rsa -f /root/.ssh/id_rsa -N ''

# Disable SELINUX

sed -i -e 's/SELINUX=enforcing/SELINUX=disabled/' /etc/selinux/config
setenforce 0

You can also choose not to disable selinux but install luna-selinux package

# Configure xinetd

mkdir /tftpboot
sed -e 's/^\(\W\+disable\W\+\=\W\)yes/\1no/g' -i /etc/xinetd.d/tftp
sed -e 's|^\(\W\+server_args\W\+\=\W-s\W\)/var/lib/tftpboot|\1/tftpboot|g' -i /etc/xinetd.d/tftp
cp /usr/share/ipxe/undionly.kpxe /tftpboot/luna_undionly.kpxe

# Configure nginx and named

cp /usr/share/luna/nginx-luna.conf /etc/nginx/conf.d/luna.conf

echo 'include "/etc/named.luna.zones";' >> /etc/named.conf
touch /etc/named.luna.zones

# Enable and start services

systemctl enable nginx
systemctl enable mongod
systemctl enable named
systemctl enable xinetd

systemctl restart xinetd
systemctl restart mongod
systemctl restart nginx
systemctl restart named
```



### Generate a CentOS image

```
export OSIMAGE_PATH=/opt/luna/os/compute
mkdir -p ${OSIMAGE_PATH}/var/lib/rpm
rpm --root ${OSIMAGE_PATH} --initdb
yum -y install yum-utils
yumdownloader centos-release
rpm --root ${OSIMAGE_PATH} -ivh centos-release\*.rpm
yum --installroot=${OSIMAGE_PATH} -y groupinstall Base
yum --installroot=${OSIMAGE_PATH} -y install kernel
yum --installroot=${OSIMAGE_PATH} -y install https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
yum --installroot=${OSIMAGE_PATH} -y install luna-client*.rpm
```

#### Setup sshd, paswordless access and password for the root user in osimage

```
mkdir ${OSIMAGE_PATH}/root/.ssh
chmod 700 ${OSIMAGE_PATH}/root/.ssh

mount -t devtmpfs devtmpfs ${OSIMAGE_PATH}/dev/
chroot ${OSIMAGE_PATH}

ssh-keygen -f /etc/ssh/ssh_host_ecdsa_key -N '' -t ecdsa
abrt-auto-reporting enabled
passwd
exit
umount ${OSIMAGE_PATH}/dev/

cat /root/.ssh/id_rsa.pub >> ${OSIMAGE_PATH}/root/.ssh/authorized_keys
chmod 600 ${OSIMAGE_PATH}/root/.ssh/authorized_keys
```

### Configure a new luna cluster

```
luna cluster init --frontend_address 10.30.255.254
luna network add -n cluster -N 10.30.0.0 -P 16
luna cluster makedhcp --network cluster --start_ip 10.30.128.1 --end_ip 10.30.140.255
systemctl start lweb ltorrent
systemctl enable lweb ltorrent
luna osimage add -n compute -p ${OSIMAGE_PATH}
luna osimage pack compute
luna bmcsetup add -n base
luna network add -n ipmi -N 10.31.0.0 -P 16
luna switch add -n switch01 --oid .1.3.6.1.2.1.17.7.1.2.2.1.2 --network ipmi --ip 10.31.253.21
luna group add -n compute -o compute -N cluster
luna group change compute -b base
luna group change -n compute --bmcnetwork --setnet ipmi
luna group change compute -i BMC -A
luna group change compute -i BMC --setnet ipmi
luna node add -g compute
luna cluster makedns
```

Please note that group and corresponding node has interface named BOOTIF. This is special placeholder for interface connected to provision network. If interface is know it can be renamed or recreated. Another placeholde is BMC. It is used in ipmitool commands to set up BMC interface.

In service mode you can perform an inventory of the interfaces, local disks, BMC features

```
luna node change -n node001 --service y
```


##### (Optional) Configure storage partitioning

You can boot the nodes in diskless mode, or write your own partitioning script using:

```
luna group change -n compute --partscript -e
```

Sample partitioning script for a device called `/dev/sda`:

```
parted /dev/sda -s 'mklabel msdos'
parted /dev/sda -s 'rm 1; rm 2'
parted /dev/sda -s 'mkpart p ext2 1 256m'
parted /dev/sda -s 'mkpart p ext3 256m 100%'
parted /dev/sda -s 'set 1 boot on'

mkfs.ext2 /dev/sda1
mkfs.ext4 /dev/sda2

mount /dev/sda2 /sysroot
mkdir /sysroot/boot
mount /dev/sda1 /sysroot/boot
```

##### (Optional) Install a bootloader on the nodes using a  postscript

`cat << EOF | luna group change -n compute  --post -e`

```
mount -o bind /proc /sysroot/proc
mount -o bind /dev /sysroot/dev
chroot /sysroot /bin/bash -c "/usr/sbin/grub2-mkconfig -o /boot/grub2/grub.cfg; /usr/sbin/grub2-install /dev/sda"
umount /sysroot/dev
umount /sysroot/proc
EOF
```

## Add a node to the cluster

```
luna node add -g compute
```

A node name will be automatically generated using the default nodeXXX format

```
luna node change -n node001 -s switch01
luna node change -n node001 -p 1

```
## Start luna's services

```
systemctl ltorrent start
systemctl lweb start
```

## Check if is working properly

```
curl "http://10.30.255.254:7050/luna?step=boot"
wget "http://10.30.255.254:7050/boot/compute-vmlinuz-3.10.0-327.10.1.el7.x86_64"
curl "http://10.30.255.254:7050/luna?step=install&node=node001"
```

Also it is possible to fetch install and boot scripts for the node usin luna CLI:

```
luna node show node001 --script boot
luna node show node001 --script install
```

## Update DHCP and DNS configurations

```
luna cluster makedhcp -N cluster -s 10.30.128.1 -e 10.30.140.255
luna cluster makedns
```

## Boot a node

Luna supports multiple modes of booting a node:

- Booting from localdisk:

```
luna node change -n node001 --localboot y
```

- Booting into service mode for diagnostics:

```
luna node change -n node001 --service y
```

- Configure the BMC when booting:

```
luna node change -n node001 --setupbmc y
```
