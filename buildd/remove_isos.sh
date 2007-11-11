#!/bin/sh
# Filename:      /usr/share/grml-live/buildd/remove_isos.sh
# Purpose:       upload grml ISOs to a rsync server
# Authors:       grml-team (grml.org), (c) Michael Prokop <mika@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2 or any later version.
# Latest change: Sun Nov 11 11:45:45 CET 2007 [mika]
################################################################################

. /etc/grml/grml-buildd.conf || exit 1
[ -n "$ISO_DIR" ] || exit 2

cd $ISO_DIR || exit 3

for file in *.iso ; do
    rm -f "$file"
    rm -f "${file}".md5
done

## END OF FILE #################################################################
