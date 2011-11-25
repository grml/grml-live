#!/bin/sh

# settings for grml_live_run:
SHORTDATE=$(date +%Y%m%d)
PRODUCT_NAME=grml_sid_$SHORTDATE
SUITE=sid
CLASSES='GRMLBASE,GRML_FULL,LATEX_CLEANUP,RELEASE,I386,IGNORE'
NAME=grml
SCRIPTNAME="$(basename $0)"
ARCH=i386

# finally just source main file
. /usr/share/grml-live/buildd/execute.sh   || exit 1
