# Osimage basics

Osimage in Luna is nothing more than a path where content of / of the nodes is stored. Plus some additional parameters, as kernel version. Adding osimage to Luna means that Luna becomes informed how to reach the content. Luna does not tamper files of the osimage, so it can be easily saved for backup purposes. In other words, even if Luna database is heavily harmed or even destroyed, content of the osimages is untouched and in safe. When you delete osimage from luna luna does not delete any file.

# Adding image

You can create image from scratch. For the process see README.
When you have directory structure with all the packages installed please not to forget to install luna-client rpm into the image.

Now you can add osimage to luna:

```
# luna osimage add -n compute -p /opt/luna/os/compute
```

Good practice will be running `pack` command immediatelly after adding or cloning (see below) image.

```
# luna osimage pack compute
INFO:root:Creating tarball.
INFO:root:Done.
INFO:root:Creating torrent.
INFO:root:Done.
INFO:root:Copying kernel & packing inirtd.
INFO:root:Done.
```

After adding image please check kernel version. Luna is able to find kernel version and set it, but it unable to recognise manually-compiled kernels. Also if you need to use not recent kernel - you need to set it manually:

```
# luna osimage show compute -k
3.10.0-514.26.2.el7.x86_64
3.10.0-693.5.2.el7.x86_64 <=

# luna osimage change compute -k 3.10.0-514.26.2.el7.x86_64

# luna osimage show compute -k
3.10.0-514.26.2.el7.x86_64 <=
3.10.0-693.5.2.el7.x86_64
```

If you changed kernel version, please do not forget to re-pack the boot image. To speed up, make sense to use `--boot` argument:

```
# luna osimage pack compute -b
INFO:root:Copying kernel & packing inirtd.
INFO:root:Done.
```

# Cloning image

Easiest way to do modification on some image and have a backup is to clone it.

```
# luna osimage list
+------------+-------------------------+-------------------------------+
| Name       | Path                    | Kernel version                |
+------------+-------------------------+-------------------------------+
| compute    | /opt/luna/os/compute    | 3.10.0-514.26.2.el7.x86_64    |
+------------+-------------------------+-------------------------------+

# luna osimage clone compute --to compute2 --path /opt/luna/os/compute2
INFO:luna.osimage.compute:/opt/luna/os/compute => /opt/luna/os/compute2

# luna osimage list
+-------------+--------------------------+-------------------------------+
| Name        | Path                     | Kernel version                |
+-------------+--------------------------+-------------------------------+
| compute     | /opt/luna/os/compute     | 3.10.0-514.26.2.el7.x86_64    |
| compute2    | /opt/luna/os/compute2    | 3.10.0-514.26.2.el7.x86_64    |
+-------------+--------------------------+-------------------------------+
```

# Grabbing image

A 'lazy' and 'dirty' way to get the image is to grab content of the running node. It uses rsync under the hood. This method is heavily relies on `--grab_exclude_list` and `--grab_filesystems` option.

Those two options are used to limit content needs to be copied to the server. By default Luna provides config that could not match your environment, so `--grab_exclude_list` needs to be carefully inspected. Would not be a bad idea to run `luna osimage grab` with `--dry_run` option first.

# Kernel parameters and dracut modules

Those two are important if you need to change boot process. For example if you need to add iSCSI disks on boot to place osimage on it is needed to add `iscsi` dracut module to initrd:

```
luna osimage change compute --dracutmodules 'luna,-i18n,-plymouth,iscsi'
```

Minus sign means that we need not to add some modules to initrd image. (`--omit` key for `dracut` command)
To get the list of the available modules see `dracut --list-modules` output.

Common task is to change kernel options. For example to enable verbosity to the boot process:

```
# luna osimage change compute --kernopts 'rd.debug'
```

Here is the place where SOL console settings can be configured.

# Lchroot

Lchroot is a 'chroot-on-steroids'. It is integrated with luna, so you can run

```
# lchroot compute
```
Handy feature - it mounts and unmount (on exit) /dev /proc and /sys filesystems
Another usefull feature is to mock uname system call:

```
# uname -r
3.10.0-514.26.2.el7.x86_64

# luna osimage show compute -k
3.10.0-514.26.2.el7.x86_64
3.10.0-693.5.2.el7.x86_64 <=

# lchroot compute
IMAGE PATH: /opt/luna/os/compute
chroot [root@compute /]$ uname -r
3.10.0-693.5.2.el7.x86_64
```
