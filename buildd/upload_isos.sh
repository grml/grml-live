#!/bin/sh
# Filename:      /usr/share/grml-live/buildd/upload_isos.sh
# Purpose:       upload grml ISOs to a rsync server
# Authors:       grml-team (grml.org), (c) Michael Prokop <mika@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2 or any later version.
# Latest change: Mon Oct 22 19:50:36 CEST 2007 [mika]
################################################################################

. /etc/grml/grml-buildd.conf || exit 1
[ -n "$RSYNC_MIRROR" ] || exit 2
[ -n "$ISO_DIR" ] || exit 3

cd $ISO_DIR || exit 4

umask 002
for file in *.iso ; do
    [ -f "${file}.md5" ] || md5sum $file > ${file}.md5
    chmod 664 $file
    chmod 664 ${file}.md5
done
rsync --partial -az --quiet $ISO_DIR/* $RSYNC_MIRROR

## END OF FILE #################################################################
