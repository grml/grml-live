#!/bin/sh
# Filename:      upload_isos.sh
# Purpose:       upload generated ISOs to daily.grml.org
# Authors:       grml-team (grml.org), (c) Michael Prokop <mika@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2 or any later version.
# Latest change: Sun Oct 07 13:06:09 CEST 2007 [mika]
################################################################################

cd /grml-live/grml-isos || exit 1
for file in *.iso ; do
    [ -f "${file}.md5" ] || md5sum $file > $file.md5
done
rsync --partial -az --quiet /grml-live/grml-isos/* grml-build@debian.netcologne.de:/home/ftp/www.grml.org/daily/

## END OF FILE #################################################################
