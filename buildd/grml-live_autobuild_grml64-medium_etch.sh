#!/bin/sh

# settings for grml_live_run:
DATE=$(date +%Y%m%d)
ISO_NAME=grml64-medium_etch_$DATE.iso
SUITE=etch
CLASSES='GRMLBASE,GRML_MEDIUM,AMD64'
NAME=grml64-medium
SCRIPTNAME="$(basename $0)"
ARCH=amd64

. /usr/share/grml-live/buildd/functions.sh || exit 1

# execute grml-live:
grml_live_run

# create_logs
upload_logs

iso_details

send_mail

store_iso

bailout
