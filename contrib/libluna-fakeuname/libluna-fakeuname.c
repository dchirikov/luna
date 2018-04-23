#include <unistd.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <sys/utsname.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

int uname(struct utsname *buf) {
    int ret;
    ret = syscall(SYS_uname, buf);
    char *fake_kern_ver = NULL;
    fake_kern_ver = (char *)getenv("FAKE_KERN");
    if (fake_kern_ver != NULL) {
        strcpy(buf->release, fake_kern_ver);
    }
    return ret;
}

