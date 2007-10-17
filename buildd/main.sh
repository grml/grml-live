#!/bin/sh
# Filename:      main.sh
# Purpose:       main configuration and function file for grml-live buildd
# Authors:       grml-team (grml.org), (c) Michael Prokop <mika@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2 or any later version.
# Latest change: Don Okt 18 00:32:02 CEST 2007 [mika]
################################################################################

# configuration:
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/bin/X11
DATE=$(date +%Y%m%d)
STORAGE=/grml-live/
OUTPUT_DIR="${STORAGE}/grml-live_${DATE}.$$"
TMP_DIR=$(mktemp -d)
MUTT_HEADERS=$(mktemp)
ATTACHMENT=$TMP_DIR/grml-live-logs_$DATE.tar.gz
[ -n "$ARCH" ] && GRML_LIVE_ARCH="-a $ARCH"
[ -n "$TMP_DIR" ] || exit 10
[ -n "$MUTT_HEADERS" ] || exit 20
RECIPIENT=root@localhost
ISO_DIR=/grml-live/grml-isos
echo "my_hdr From: grml-live autobuild daemon <root@localhost>" > $MUTT_HEADERS

# execute grml-live:
grml_live_run() {
grml-live -F $GRML_LIVE_ARCH -s $SUITE -c $CLASSES -o $OUTPUT_DIR \
          -g $NAME -v $DATE -r grml-live-autobuild -i $ISO_NAME \
	  1>/var/log/fai/dirinstall/grml/grml-live.stdout \
	  2>/var/log/fai/dirinstall/grml/grml-live.stderr ; RC=$?

if [ "$RC" = "0" ] ; then
   RC=success
else
   RC=error
fi
}

create_logs() {
# create log archive:
tar zcf $ATTACHMENT /var/log/fai/dirinstall/grml 1>/dev/null
}

iso_details() {
if ! [ -f "$OUTPUT_DIR/grml_isos/$ISO_NAME" ] ; then
   ISO_DETAILS="There was an error creating $ISO_NAME"
else
   ISO_DETAILS=$(ls -lh $OUTPUT_DIR/grml_isos/$ISO_NAME)
fi
}

send_mail() {
# send status mail:
echo -en "Automatically generated mail by $SCRIPTNAME

$ISO_DETAILS

Return code of grml-live run was: $RC

The following errors have been noticed (several might be warnings only):

$(grep error /var/log/fai/dirinstall/grml/* | grep -ve liberror -ve libgpg-error)

The following warnings have been noticed:

$(grep warn /var/log/fai/dirinstall/grml/*)

Find details in the attached logs." | \
mutt -s "grml-live_autobuild_grml-large_sid.sh [${DATE}] - $RC" \
     -a $ATTACHMENT \
     $RECIPIENT
}

store_iso() {
# make sure we store the final iso:
[ -d "$ISO_DIR" ] || mkdir "$ISO_DIR"
mv $OUTPUT_DIR/grml_isos/$ISO_NAME $ISO_DIR
}

bailout() {
  rm -rf "$TMP_DIR" "$MUTT_HEADERS" "$OUTPUT_DIR"
}

trap bailout 1 2 3 15

## END OF FILE #################################################################
