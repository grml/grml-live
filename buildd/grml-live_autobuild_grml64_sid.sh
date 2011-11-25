#!/bin/sh

# settings for grml_live_run:
SHORTDATE=$(date +%Y%m%d)
PRODUCT_NAME=grml64_sid_$SHORTDATE
SUITE=sid
CLASSES='GRMLBASE,GRML_FULL,LATEX_CLEANUP,RELEASE,AMD64,IGNORE'
NAME=grml64
SCRIPTNAME="$(basename $0)"
ARCH=amd64

# finally just source main file
. /usr/share/grml-live/buildd/execute.sh   || exit 1
