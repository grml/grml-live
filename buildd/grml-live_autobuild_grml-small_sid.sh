#!/bin/sh

# settings for grml_live_run:
SHORTDATE=$(date +%Y%m%d)
PRODUCT_NAME=grml-small_sid_$SHORTDATE
SUITE=sid
CLASSES='GRMLBASE,GRML_SMALL,RELEASE,I386,IGNORE'
NAME=grml-small
SCRIPTNAME="$(basename $0)"
ARCH=i386

# finally just source main file
. /usr/share/grml-live/buildd/execute.sh   || exit 1
