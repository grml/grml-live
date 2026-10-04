#!/bin/sh
#
# This file was deployed via grml-live's
# ${GRML_FAI_CONFIG}/scripts/GRMLBASE/80-initramfs script, using
# ${GRML_FAI_CONFIG}/files/GRMLBASE/usr/lib/dracut/modules.d/50grml/grml-emergency.sh
#
# Filename:      /usr/lib/dracut/modules.d/50grml/grml-emergency.sh
# Purpose:       Provide emergency shell without root password prompt in dracut
# Authors:       grml-team (grml.org),
#                (c) Chris Hofstaedtler <ch@grml.org>,
#                Red Hat, Inc., Harald Hoyer <harald@redhat.com>, Jeremy Katz <katzj@redhat.com>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2 or any later version.
################################################################################
# shellcheck shell=ash

# Partially copied from dracut-lib.sh; cannot call _emergency_shell
# as that would end in a recursive call of ourselves.

. /etc/os-release
echo 'Grml: Early boot (initramfs) failed.'
echo 'Grml: Dropping to debug shell.'
echo "Grml: Version: ${PRETTY_NAME}"
echo
echo 'Grml: try correcting root=live:... on your next boot'
echo
export PS1="grml:\${PWD}# "
[ -e /.profile ] || : > /.profile

_ctty=console
while [ -f "/sys/class/tty/$_ctty/active" ]; do
    read -r _ctty < "/sys/class/tty/$_ctty/active"
    _ctty=${_ctty##* } # last one in the list
done
_ctty=/dev/$_ctty
[ -c "$_ctty" ] || _ctty=/dev/tty1

setsid --ctty /bin/sh -i -l 0<> "$_ctty" 1<> "$_ctty" 2<> "$_ctty"

exit 0
