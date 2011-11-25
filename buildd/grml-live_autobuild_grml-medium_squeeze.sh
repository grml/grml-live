#!/bin/sh

# settings for grml_live_run:
SHORTDATE=$(date +%Y%m%d)
PRODUCT_NAME=grml-medium_squeeze_$SHORTDATE
SUITE=squeeze
CLASSES='GRMLBASE,GRML_MEDIUM,RELEASE,I386,IGNORE'
NAME=grml-medium
SCRIPTNAME="$(basename $0)"
ARCH=i386

# finally just source main file
. /usr/share/grml-live/buildd/execute.sh   || exit 1
