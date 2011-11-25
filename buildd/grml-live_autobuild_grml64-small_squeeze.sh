#!/bin/sh

# settings for grml_live_run:
SHORTDATE=$(date +%Y%m%d)
PRODUCT_NAME=grml64-small_squeeze_$SHORTDATE
SUITE=squeeze
CLASSES='GRMLBASE,GRML_SMALL,RELEASE,AMD64,IGNORE'
NAME=grml64-small
SCRIPTNAME="$(basename $0)"
ARCH=amd64

# finally just source main file
. /usr/share/grml-live/buildd/execute.sh   || exit 1
