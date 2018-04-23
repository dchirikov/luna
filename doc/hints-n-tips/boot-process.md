# Booting nodes

Boot process is quite stright-forward. Firstly node needs to be configured to support PXE boot.

- When PXE network card's microcode took controll it sends DHCP broadcast in order to find DHCP server and acquire IP address.
- DHCP server, in its turn, provides requested IP address and 2 important options: name of the bootable file and IP adress of the server where this file can be found. In our case bootable file is iPXE binary.
- Node downloads this file using tftp protocol and iPXE takes control.
- iPXE sends another DHCP requests in order to find what to do next.
- DHCP server recognizes that second requests is beind send by iPXE, but not the network card's microcode inspecting `user-class` option in request.
- For this second request, DHCP server provides http URL. The exact URL (`.../luna?step=boot`) can be found in `/etc/dhcp/dhcpd.conf`. And for debug purposes this URL can be fetched using `curl`.
- iPXE downloads the content of this url and render menu ("blue boot-menu")
- Then boot process is spinning on the very first menu option. Node is sending all available MAC addresses in GET http request to Luna server and tries to get path to the kernel, kernel options and path to initrd file. Those requests should be logged in nginx logs: `.../luna?step=discovery...`
- Luna server (lweb daemon) tries to match all MAC addresses from request to all the nodes configured in DB. In background, lweb scans all the configured switches and cache their learned MAC adresses. If mac address is not configured for node, web tries to use this cache to match node MACs from GET and switch/port pair if latter is configured for the node. If corresponding node is found based on switch/port pair MAC address for this node will be filled in DB. It will be seen in `luna node show` output.
- If lweb is unable to find the node, 404 answer will be send to the node and iPXE will re-send request in 10 sec. Lweb will use this time to fill the MAC cache or engineer can configure MAC address manually for the node.
- If node is 'known' for Luna, boot options will be send as an answer. It will include path to bootable files and other options.
- Node downloads kernel and initrd. Those files are located in `~luna/boot`. And are being prepared during `osimage pack` operation. Boot options can be found in `/proc/cmdline` later on the node.
- Initrd has small luna dracut module (the one is being installed in luna-client rpm). This module performs several things. It temporarily configures interfaces, runs sshd and makes shell availeble on tty2 (Alt+F2).
- Inspecting `/proc/cmdline` Luna dracut module knows how to reach provisioning server. It uses curl to fetch install script. This script can be seen in `luna node show ... --script install` or by `curl .../luna?step=install...` request.


# Basic install script logic

- Pre-script is being executed first.
- If bmcsetup is assigned to group and setupbmc is turned to 'yes' then ipmitool commands will be issued to configure BMC
- Partition script goes next. It should partition and mount block device or tmpfs/ramfs to `/sysroot` directory inside dracut environment. See examples in `man luna`.
- Then script will download torrent file from server and start downloading content. Install script spawns torrent-client in a backgrouund and then wait when torrent-client send SIGUSR1 signal back. This signal means that tarball is downloaded and can be exatracted to `/sysroot`
- Unpacking torrent install script is having torrent-client running in a background and seeding tarball.
- When unpacking done SIGTERM is being sent to torrent-client and tarball deleted.
- On this point content of the tarball is identical to the one server has in osimage path.
- Several files, as `/proc/sys/kernel/hostname`, `/etc/sysconfig/network`, `/etc/hostname` and `/etc/sysconfig/network-scripts/ifcfg-*` will be changed in order to asign hostname and configure IP addresses on boot.
- Custom postscript will be executed.
- Several scripts regarding selinux and capabilities is being executed.

# Finishig up

Now system is ready to continue to boot to OS. So Luna dracut environment kills shell on tty2, stops sshd and unasign IP addresses. After that it exits and let system boots - switch root and run systemd services.

