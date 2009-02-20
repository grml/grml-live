#!/bin/sh
# Filename:      /usr/share/grml-live/buildd/link_latest.sh
# Purpose:       create symlinks to the most recent snapshot ISOs
# Authors:       grml-team (grml.org), (c) Michael Prokop <mika@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2 or any later version.
################################################################################

set -e

. /etc/grml/grml-buildd.conf

[ -n "$MIRROR_DIRECTORY" ] || exit 1
cd $MIRROR_DIRECTORY || exit 2

for flavour in grml-small_lenny grml-small_sid grml-medium_lenny grml-medium_sid grml_sid grml_lenny \
               grml64-small_lenny grml64-small_sid grml64-medium_lenny grml64-medium_sid grml64_sid grml64_lenny ; do
  ISO="$(ls -1 $flavour/*.iso | tail -1)"
  if [ -n "$ISO" ] ; then
     ln -sf $ISO $(basename ${ISO%%_[0-9]*})_latest.iso
     ln -sf ${ISO}.md5 $(basename ${ISO%%_[0-9]*})_latest.iso.md5
     ln -sf ${ISO}.sha1 $(basename ${ISO%%_[0-9]*})_latest.iso.sha1
  fi
done

## END OF FILE #################################################################
