#!/bin/sh
. main.sh || exit 1
umask 002
cd /srv/grml-isos || exit 1
for file in *.iso ; do
    [ -f "${file}.md5" ] || md5sum $file > ${file}.md5
    chmod 664 $file
    chmod 664 ${file}.md5
done
rsync --partial -az --quiet $ISO_DIR/* grml-build@debian.netcologne.de:/home/ftp/www.grml.org/daily/
