#!/bin/sh

# settings for grml_live_run:
DATE=$(date +%Y%m%d)
ISO_NAME=grml-small_wheezy_$DATE.iso
SUITE=wheezy
CLASSES='GRMLBASE,GRML_SMALL,REMOVE_DOCS,RELEASE,I386,IGNORE'
NAME=grml-small
SCRIPTNAME="$(basename $0)"
ARCH=i386

# finally just source main file
. /usr/share/grml-live/buildd/execute.sh   || exit 1
