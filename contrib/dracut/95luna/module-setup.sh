#!/bin/bash

check() {
    return 0
}

depends() {
    echo network
    echo nss-softokn
    return 0
}

install() {
    dracut_install ssh sshd scp tar wget curl awk sed gzip basename dd partx \
                   parted mkfs.ext2 mkfs.ext3 mkfs.ext4 mkfs.xfs ipmitool \
                   blkdiscard fstrim nslookup dig
    inst_libdir_file libnssdbm3.so libnsspem.so libsoftokn3.chk \
                     libsoftokn3.so libsqlite3.so

    inst "$moddir/sshd_config" "/etc/ssh/sshd_config"
    inst "$moddir/bashrc" "/root/.bashrc"
    inst "$moddir/profile" "/root/.profile"
    inst_simple /etc/ssh/ssh_host_rsa_key
    inst_simple /etc/ssh/ssh_host_ecdsa_key
    inst_simple /etc/ssh/ssh_host_ed25519_key
    inst_simple /etc/pki/tls/certs/ca-bundle.crt
    mkdir -m 0700 -p "$initdir/root/.ssh"
    inst_simple /root/.ssh/authorized_keys

    inst_simple /etc/resolv.conf

    mkdir -m 0755 -p "$initdir/luna"
    inst "$moddir/ltorrent-client" "/luna/ltorrent-client"

    inst_hook cmdline 99 "$moddir/luna-parse-cmdline.sh"
    inst_hook initqueue/finished 99 "$moddir/luna-start.sh"

}
