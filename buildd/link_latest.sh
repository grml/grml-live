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

DAILY_DIR=/srv/mirror/www.grml.org/daily

cd "$DAILY_DIR"
echo "---------------------------" >> "$DAILY_DIR"/.timestamp_link
for flavour in grml-medium_squeeze   grml-medium_wheezy   grml-medium_sid   grml-small_squeeze   grml-small_wheezy  grml-small_sid \
               grml64-medium_squeeze grml64-medium_wheezy grml64-medium_sid grml64-small_squeeze grml64-small_wheezy grml64-small_sid \
               grml64_squeeze grml64_wheezy grml64_sid grml_squeeze grml_wheezy grml_sid ; do
  ISO="$(ls -1 $flavour/*.iso | tail -1)"
  if [ -n "$ISO" ] ; then
     latest="$(basename ${ISO%%_[0-9]*})_latest.iso"
     ln -sf $ISO ${latest}
     # ln -sf ${ISO}.md5 ${latest}.md5
     # http://bts.grml.org/grml/issue814
     name=$(awk '{print $2}' "${ISO}".md5)
     sed "s/$name/$latest/" "${ISO}".md5 > "${latest}".md5
     echo "$ISO" >> "$DAILY_DIR"/.timestamp_link
  fi
done
echo "---------------------------" >> "$DAILY_DIR"/.timestamp_link

## END OF FILE #################################################################
