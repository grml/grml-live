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

cd "$DAILY_DIR"
echo "---------------------------" >> "$DAILY_DIR"/.timestamp_link
for flavour in grml-medium_lenny   grml-medium_squeeze   grml-medium_sid   grml-small_lenny   grml-small_squeeze  grml-small_sid \
               grml64-medium_lenny grml64-medium_squeeze grml64-medium_sid grml64-small_lenny grml64-small_squeeze grml64-small_sid \
               grml64_lenny grml64_squeeze grml64_sid grml_lenny grml_squeeze grml_sid ; do
  ISO="$(ls -1 $flavour/*.iso | tail -1)"
  if [ -n "$ISO" ] ; then
     ln -sf $ISO $(basename ${ISO%%_[0-9]*})_latest.iso
     ln -sf ${ISO}.md5 $(basename ${ISO%%_[0-9]*})_latest.iso.md5
     ln -sf ${ISO}.sha1 $(basename ${ISO%%_[0-9]*})_latest.iso.sha1
  fi
done

## END OF FILE #################################################################
