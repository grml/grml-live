Security considerations for grml
================================

1.) There is no automatic start of external accessible services in Live-CD
    mode. (sshd is started by default on harddisk installations though.)

2.) There are no default passwords. All accounts are locked by default.
    Even local logins are not possible (unless you set a password or create
    new user accounts as root).

3.) Therefore, all local interactive processes are started by init without
    authorization.
    Programs that only work for root are usually started using sudo without
    password. This has the advantage of making faults caused by defective
    software very unlikely, but does not enhance local security, since it
    is fairly easy to switch between the "grml" and "root" account. The
    grml user should never be allowed for external logins (in the case
    that sshd or similar servers are being launched).

4.) You can create valid passwords using "sudo passwd [username]" from the
    shell, individually.

GRML squashfs file
==================

The GRML squashfs file has been moved from /GRML/GRML to
/live/grml.squashfs due to the use of live-initramfs.
