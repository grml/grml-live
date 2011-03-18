#!/bin/sh
# Filename:      /usr/share/grml-live/buildd/link_latest.sh
# Purpose:       create symlinks to the most recent snapshot ISOs
# Authors:       grml-team (grml.org), (c) Michael Prokop <mika@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2 or any later version.
################################################################################

set -e

dir="$(dirname $0)"

if [ -r /etc/grml/grml-buildd.conf ] ; then
  . /etc/grml/grml-buildd.conf
elif [ -r "${dir}/grml-buildd.conf" ] ; then
  . "${dir}/grml-buildd.conf"
fi

# directory where daily ISOs are stored locally
if [ -z "$MIRROR_DIRECTORY" ] ; then
  echo "Error: \$MIRROR_DIRECTORY is not set. Exiting." >&2
  exit 1
fi

if ! cd "$MIRROR_DIRECTORY" ; then
  echo "Error: could not change directory to $MIRROR_DIRECTORY" >&2
  exit 1
fi

echo "---------------------------" >> "$MIRROR_DIRECTORY"/.timestamp_link
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
     name=$(awk '{print $2}' "${ISO}".sha1)
     sed "s/$name/$latest/" "${ISO}".sha1 > "${latest}".sha1
     echo "$ISO" >> "$MIRROR_DIRECTORY"/.timestamp_link
  fi
done
echo "---------------------------" >> "$MIRROR_DIRECTORY"/.timestamp_link

## END OF FILE #################################################################
