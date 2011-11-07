#!/bin/sh

# settings for grml_live_run:
DATE=$(date +%Y%m%d)
ISO_NAME=grml64-small_sid_$DATE.iso
SUITE=sid
CLASSES='GRMLBASE,GRML_SMALL,RELEASE,AMD64,IGNORE'
NAME=grml64-small
SCRIPTNAME="$(basename $0)"
ARCH=amd64

# finally just source main file
. /usr/share/grml-live/buildd/execute.sh   || exit 1
