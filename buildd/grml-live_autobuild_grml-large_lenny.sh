#!/bin/sh

# settings for grml_live_run:
DATE=$(date +%Y%m%d)
ISO_NAME=grml_lenny_$DATE.iso
SUITE=lenny
CLASSES='GRMLBASE,GRML_FULL,LATEX_CLEANUP,RELEASE,I386'
NAME=grml
SCRIPTNAME="$(basename $0)"
ARCH=i386

# finally just source main file
. /usr/share/grml-live/buildd/execute.sh   || exit 1
