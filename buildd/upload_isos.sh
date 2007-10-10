#!/bin/sh
# Filename:      upload_isos.sh
# Purpose:       upload generated ISOs to daily.grml.org
# Authors:       grml-team (grml.org), (c) Michael Prokop <mika@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2 or any later version.
# Latest change: Mit Okt 10 09:46:08 CEST 2007 [mika]
################################################################################

cd /grml-live/grml-isos || exit 1
for file in *.iso ; do
    [ -f "${file}.md5" ] || md5sum $file > $file.md5
    chmod 664 $file
    chmod 664 ${file}.md5
done
umask 002
rsync --partial -az --quiet /grml-live/grml-isos/* grml-build@debian.netcologne.de:/home/ftp/www.grml.org/daily/

## END OF FILE #################################################################
