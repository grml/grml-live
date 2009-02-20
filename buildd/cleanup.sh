#!/bin/sh
# Filename:      cleanup.sh
# Purpose:       clean up daily builds directory - remove old files
# Authors:       grml-team (grml.org), (c) Michael Prokop <mika@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2 or any later version.
################################################################################

set -e

. /etc/grml/grml-buildd.conf

[ -n "$MIRROR_DIRECTORY" ] || exit 1
cd $MIRROR_DIRECTORY || exit 2

# we want to always keep a few images, no matter how old they are
# but get rid of the oldest ones first of course :)
# so: how many images do we want to keep? DAYS=3 usually means 'keep 4 images'
DAYS=3

REMOVE_ME=""
for flavour in grml-small_lenny grml-small_sid grml-medium_lenny grml-medium_sid grml_sid grml_lenny \
               grml64-small_lenny grml64-small_sid grml64-medium_lenny grml64-medium_sid grml64_sid grml64_lenny ; do
  FILE_COUNT=$(ls -1 $flavour/$flavour*.iso | wc -l)
  if [ "$FILE_COUNT" -gt "$DAYS" ] ; then
     FILES=$(ls -1 $flavour/$flavour*.iso | tail -"$DAYS")
     OLD_FILES=$(ls $flavour/$flavour*.iso | grep -v "$FILES")
     for file in $OLD_FILES ; do
         REMOVE_ME="$REMOVE_ME $(find "$file" -mtime +$DAYS)"
     done
  fi
done

[ -d .archive ] || mkdir .archive

for file in $REMOVE_ME ; do
    # remove ISOs:
    test -f "${file}"      && rm -f "$file"
    # ... but keep their md5sum / sha1sum:
    test -f "${file}".md5  && mv "${file}".md5   .archive
    test -f "${file}".sha1 && mv "${file}".sha1 .archive
done

# inform on successful removal:
if [ "$(echo "$REMOVE_ME" | tr -d ' ' )" != "" ] ; then
   echo "deleted files $REMOVE_ME" | mail -s "daily-builds cleanup script" mika@grml.org
fi

## END OF FILE #################################################################
