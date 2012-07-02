Security considerations for Grml
================================

1.) There are no default passwords. All accounts are locked by default.
    Even local logins are not possible by default (unless you set a password
    or create new user accounts as root).

2.) Therefore, all local interactive processes are started by init without
    authorization.
    Programs that only work for root are usually started using sudo without
    password. This has the advantage of making faults caused by defective
    software very unlikely, but does not enhance local security, since it
    is fairly easy to switch between the "grml" and "root" account. The
    grml user should never be allowed for external logins (in the case
    that sshd or similar servers are being launched).

3.) You can create valid passwords using "sudo passwd [username]" from the
    shell, individually.
