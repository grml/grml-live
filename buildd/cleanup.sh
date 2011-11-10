#!/bin/sh
# Filename:      cleanup.sh
# Purpose:       clean up daily builds directory - remove old files
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

# mail address where reports should be sent to
if [ -z "$STORAGE_ADMIN" ] ; then
  echo "Error: \$STORAGE_ADMIN is not set. Exiting." >&2
  exit 2
fi

if ! cd "$MIRROR_DIRECTORY" ; then
  echo "Error: could not change directory to $MIRROR_DIRECTORY" >&2
  exit 3
fi

# we want to always keep a few images, no matter how old they are
# but get rid of the oldest ones first of course :)
# so: how many images do we want to keep? DAYS=3 usually means 'keep 4 images'
DAYS=3

REMOVE_ME=""
for flavour in grml-medium_wheezy   grml-medium_sid   grml-small_wheezy   grml-small_sid \
               grml64-medium_wheezy grml64-medium_sid grml64-small_wheezy grml64-small_sid \
               grml64_wheezy        grml64_sid        grml_wheezy         grml_sid ; do
  FILE_COUNT=$(ls -1 $flavour/$flavour*.iso | wc -l)
  if [ "$FILE_COUNT" -gt "$DAYS" ] ; then
     FILES=$(ls -1 $flavour/$flavour*.iso | tail -"$DAYS")
     OLD_FILES=$(ls $flavour/$flavour*.iso | grep -v "$FILES")
     for file in $OLD_FILES ; do
         REMOVE_ME="$REMOVE_ME $(find $file -mtime +$DAYS)"
     done
  fi
done

[ -d .archive ] || mkdir .archive

for file in $REMOVE_ME ; do
    test -f ${file}     && rm -f $file
    # ... but keep their md5sum / sha1sum:
    test -f ${file}.md5  && mv ${file}.md5  .archive
    test -f ${file}.sha1 && mv ${file}.sha1 .archive
done

# inform on successful removal:
if [ "$(echo "$REMOVE_ME" | tr -d ' ' )" != "" ] ; then
   echo "deleted files $REMOVE_ME" | mail -s "daily-builds cleanup script" "$STORAGE_ADMIN"
fi

## END OF FILE #################################################################
