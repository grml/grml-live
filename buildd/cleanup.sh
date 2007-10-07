#!/bin/sh
# Filename:      cleanup.sh
# Purpose:       clean up daily builds directory - remove old files
# Authors:       grml-team (grml.org), (c) Michael Prokop <mika@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2 or any later version.
# Latest change: Sun Oct  7 09:29:22 UTC 2007 [mika]
################################################################################

set -e

# we want to always keep a few images, no matter how old they are
# but get rid of the oldest ones first of course :)
# so: how many images do we want to keep?
DAYS=3

REMOVE_ME=""
for flavour in grml-medium_etch grml-medium_sid grml64-medium_etch grml64-medium_sid grml64_sid grml_sid ; do
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
    test -f ${file}     && mv $file .delete
    test -f ${file}.md5 && mv ${file}.md5 .delete
done

# inform on successful removal:
if [ "$(echo "$REMOVE_ME" | tr -d ' ' )" != "" ] ; then
   echo "deleted files $REMOVE_ME" | mail -s "daily-builds cleanup script" mika@grml.org
fi

# EOF
