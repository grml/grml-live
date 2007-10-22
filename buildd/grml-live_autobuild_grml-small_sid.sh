#!/bin/sh

# settings for grml_live_run:
DATE=$(date +%Y%m%d)
ISO_NAME=grml-small_sid_$DATE.iso
SUITE=sid
CLASSES='GRMLBASE,GRML_SMALL,REMOVE_DOCS,I386'
NAME=grml-small
SCRIPTNAME="$(basename $0)"
ARCH=i386

. /usr/share/grml-live/buildd/functions.sh || exit 1

# execute grml-live:
grml_live_run

create_logs

iso_details

send_mail

store_iso

bailout
