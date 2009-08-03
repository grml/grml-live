#!/bin/sh

# settings for grml_live_run:
DATE=$(date +%Y%m%d)
ISO_NAME=grml-small_squeeze_$DATE.iso
SUITE=squeeze
CLASSES='GRMLBASE,GRML_SMALL,REMOVE_DOCS,RELEASE,I386'
NAME=grml-small
SCRIPTNAME="$(basename $0)"
ARCH=i386

# finally just source main file
. /usr/share/grml-live/buildd/execute.sh   || exit 1
