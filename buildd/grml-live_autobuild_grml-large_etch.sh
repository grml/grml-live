#!/bin/sh

. main.sh || exit 1

# settings for grml_live_run:
ISO_NAME=grml_etch_$DATE.iso
SUITE=etch
CLASSES='GRMLBASE,GRML_FULL,LATEX_CLEANUP,RELEASE,I386'
NAME=grml
SCRIPTNAME="$(basename $0)"
ARCH=i386

# execute grml-live:
grml_live_run

create_logs

iso_details

send_mail

store_iso

bailout
