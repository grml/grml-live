#!/bin/sh
# Filename:      /usr/share/grml-live/buildd/link_latest.sh
# Purpose:       create symlinks to the most recent snapshot ISOs
# Authors:       grml-team (grml.org), (c) Michael Prokop <mika@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2 or any later version.
# Latest change: Sun Dec 09 18:02:45 CET 2007 [mika]
################################################################################

set -e

. /etc/grml/grml-buildd.conf

[ -n "$MIRROR_DIRECTORY" ] || exit 1
cd $MIRROR_DIRECTORY || exit 2

for flavour in grml-small_etch grml-small_sid grml-medium_etch grml-medium_sid grml_sid grml_etch \
               grml64-small_etch grml64-small_sid grml64-medium_etch grml64-medium_sid grml64_sid grml64_etch ; do
  ISO="$(ls -1 $flavour/*.iso | tail -1)"
  if [ -n "$ISO" ] ; then
     ln -sf $ISO $(basename ${ISO%%_[0-9]*})_latest.iso
     ln -sf ${ISO}.md5 $(basename ${ISO%%_[0-9]*})_latest.iso.md5
  fi
done

## END OF FILE #################################################################
