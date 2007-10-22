#!/bin/sh

# settings for grml_live_run:
DATE=$(date +%Y%m%d)
ISO_NAME=grml64_sid_$DATE.iso
SUITE=sid
CLASSES='GRMLBASE,GRML_FULL,LATEX_CLEANUP,AMD64'
NAME=grml64
SCRIPTNAME="$(basename $0)"

. /usr/share/grml-live/buildd/buildd/functions.sh || exit 1

# execute grml-live:
grml_live_run

create_logs

iso_details

send_mail

store_iso

bailout
