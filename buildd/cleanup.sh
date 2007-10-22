#!/bin/sh
# Filename:      /usr/share/grml-live/buildd/buildd/cleanup.sh
# Purpose:       clean up daily builds directory - remove old files
# Authors:       grml-team (grml.org), (c) Michael Prokop <mika@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2 or any later version.
# Latest change: YDATE [mika]
################################################################################

set -e

. /etc/grml/grml-buildd.conf

[ -n "$RECIPIENT" ] || RECIPIENT=root@localhost

[ -n "$MIRROR_DIRECTORY" ] || exit 1
cd $MIRROR_DIRECTORY || exit 2

# we want to always keep a few images, no matter how old they are
# but get rid of the oldest ones first of course :)
# so: how many images do we want to keep?
DAYS=3

REMOVE_ME=""
for flavour in grml-small_etch grml-small_sid grml-medium_etch grml-medium_sid grml_sid grml_etch \
               grml64-small_etch grml64-small_sid grml64-medium_etch grml64-medium_sid grml64_sid grml64_etch ; do
  FILE_COUNT=$(ls -1 $flavour*.iso | wc -l)
  if [ "$FILE_COUNT" -gt "$DAYS" ] ; then
     FILES=$(ls -1 $flavour*.iso | tail -"$DAYS")
     OLD_FILES=$(ls $flavour*.iso | grep -v "$FILES")
     for file in $OLD_FILES ; do
         REMOVE_ME="$REMOVE_ME $(find $file -mtime +$DAYS)"
     done
  fi
done

[ -d .delete ] || mkdir .delete

# move them before we really delete them:
for file in $REMOVE_ME ; do
    test -f ${file}     && rm -f $file
    test -f ${file}.md5 && mv ${file}.md5 .delete
done

# inform on successful removal:
if [ "$(echo "$REMOVE_ME" | tr -d ' ' )" != "" ] ; then
   echo "deleted files $REMOVE_ME" | mail -s "daily-builds cleanup script" $RECIPIENT
fi

## END OF FILE #################################################################
