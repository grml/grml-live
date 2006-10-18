#!/bin/bash
# Filename:      automount.sh
# Purpose:       generate an automounter entry automatically for automount /mnt/auto program this_script
# Authors:       (c) Klaus Knopper 2002, (c) Michael Prokop <mika@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2.
# Latest change: Don Okt 28 16:19:40 CEST 2004 [mika]
################################################################################

# WARNING: This script is used for removable media in grml,
# therefore the mount is always read-write (except for cdroms
# and ntfs).

# Defaults
rw="rw"
device="/dev/${1##*/}"
case "$1" in
floppy)     [ -s /etc/sysconfig/floppy ] || exit 1; device="/dev/fd0";;
cdrom*)     rw="ro";;
dvd*)       rw="ro";;
esac

# Uses external fstype script from grml-scanpartitions
fs="$(fstype "$device")"

[ "$?" = "0" ] || exit 1

case "$fs" in
*fat|msdos) options="${rw},uid=grml,gid=grml,umask=000";;
ntfs)       options="ro,uid=grml,gid=grml,umask=0222";;
iso9660)    options="ro";;
*)          options="${rw}";;
esac

MNTLINE="-fstype=$fs,users,exec,$options	:$device"

# Return line to the automounter
echo "$MNTLINE"

## END OF FILE #################################################################
