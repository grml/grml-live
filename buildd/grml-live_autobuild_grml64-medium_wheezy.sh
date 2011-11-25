#!/bin/sh

# settings for grml_live_run:
SHORTDATE=$(date +%Y%m%d)
PRODUCT_NAME=grml64-medium_wheezy_$SHORTDATE
SUITE=wheezy
CLASSES='GRMLBASE,GRML_MEDIUM,RELEASE,AMD64,IGNORE'
NAME=grml64-medium
SCRIPTNAME="$(basename $0)"
ARCH=amd64

# finally just source main file
. /usr/share/grml-live/buildd/execute.sh   || exit 1
