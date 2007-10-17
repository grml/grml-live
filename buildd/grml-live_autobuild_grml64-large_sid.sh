#!/bin/sh

. main.sh || exit 1

# settings for grml_live_run:
ISO_NAME=grml64_sid_$DATE.iso
SUITE=sid
CLASSES='GRMLBASE,GRML_FULL,LATEX_CLEANUP,AMD64'
NAME=grml64
SCRIPTNAME="$(basename $0)"

# execute grml-live:
grml_live_run

create_logs

iso_details

send_mail

store_iso

bailout
