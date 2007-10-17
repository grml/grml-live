#!/bin/sh


#!/bin/sh

. main.sh || exit 1

# settings for grml_live_run:
ISO_NAME=grml-medium_etch_$DATE.iso
SUITE=sid
CLASSES='GRMLBASE,GRML_MEDIUM,RELEASE,I386'
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
