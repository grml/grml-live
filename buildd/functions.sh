#!/bin/sh
# Filename:      /usr/share/grml-live/buildd/functions.sh
# Purpose:       main function file for grml-live buildd
# Authors:       grml-team (grml.org), (c) Michael Prokop <mika@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2 or any later version.
# Latest change: Thu Oct 25 22:40:45 CEST 2007 [mika]
################################################################################

die() {
  [ -n "$1" ] && echo "$1">&2
  exit 1
}

. /etc/grml/grml-buildd.conf || die "Could not source /etc/grml/grml-buildd.conf. Exiting."

type -p mutt 1>/dev/null 2>&1 || die "mutt binary not found. Exiting."

# exit if important variables aren't set:
[ -n "$STORAGE" ]  || die "\$STORAGE is not set. Exiting."
[ -n "$SUITE" ]    || die "\$SUITE is not set. Exiting."
[ -n "$CLASSES" ]  || die "\$CLASSES is not set. Exiting."
[ -n "$NAME" ]     || die "\$NAME is not set. Exiting."
[ -n "$ISO_NAME" ] || die "\$ISO_NAME is not set. Exiting."

# some defaults:
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/bin/X11
DATE=$(date +%Y%m%d)
TMP_DIR=$(mktemp -d)
MUTT_HEADERS=$(mktemp)
[ -n "$TMP_DIR" ] || die "Could not create \$TMP_DIR. Exiting."
[ -n "$MUTT_HEADERS" ] || die "Could not create $\MUTT_HEADERS. Exiting."
[ -n "$ARCH" ] && GRML_LIVE_ARCH="-a $ARCH"

# make sure we have same safe defaults:
[ -n "$OUTPUT_DIR" ]    || OUTPUT_DIR="${STORAGE}/grml-live_${DATE}.$$"
[ -n "$ISO_DIR" ]       || ISO_DIR=$STORAGE/grml-isos
[ -n "$RECIPIENT" ]     || RECIPIENT=root@localhost
[ -n "$ATTACHMENT" ]    || ATTACHMENT=$TMP_DIR/grml-live-logs_$DATE.tar.gz
[ -n "$FAI_LOGFILES" ]  || FAI_LOGFILES=/var/log/fai/dirinstall/grml
[ -n "$GRML_LOGFILES" ] || GRML_LOGFILES=/var/log/grml-live/
[ -n "$FROM" ]          || FROM=root@localhost

[ -d "$FAI_LOGFILES" ]  || mkdir -p $FAI_LOGFILES
[ -d "$GRML_LOGFILES" ] || mkdir -p $GRML_LOGFILES

echo "my_hdr From: grml-live autobuild daemon <$FROM>" > $MUTT_HEADERS

# execute grml-live:
grml_live_run() {
  if [ -f "$ISO_DIR/$ISO_NAME" ] ; then
     echo "$ISO_DIR/$ISO_NAME exists already. Nothing to be done, exiting."
     exit 0
  fi

  grml-live -F $GRML_LIVE_ARCH -s $SUITE -c $CLASSES -o $OUTPUT_DIR \
            -g $NAME -v $DATE -r grml-live-autobuild -i $ISO_NAME \
            1>$GRML_LOGFILES/grml-buildd.stdout \
            2>$GRML_LOGFILES/grml-buildd.stderr ; RC=$?

  if [ "$RC" = "0" ] ; then
     RC_INFO=success
  else
     RC_INFO=error
  fi
}

# create log archive:
create_logs() {
  ( cd / && tar zcf $ATTACHMENT var/log/fai/dirinstall/grml 1>/dev/null )
}

# store information of ISO size:
iso_details() {
  if ! [ -f "$OUTPUT_DIR/grml_isos/$ISO_NAME" ] ; then
     ISO_DETAILS="There was an error creating $ISO_NAME"
  else
     ISO_DETAILS=$(ls -lh $OUTPUT_DIR/grml_isos/$ISO_NAME)
  fi
}

# send status mail:
send_mail() {
  echo -en "Automatically generated mail by $SCRIPTNAME

$ISO_DETAILS

Return code of grml-live run was: $RC

The following errors have been noticed (several might be warnings only):

$(grep error $FAI_LOGFILES/* | grep -ve liberror -ve libgpg-error || echo "* nothing")

The following warnings have been noticed:

$(grep warn $FAI_LOGFILES/* || echo "* nothing")

Find details in the attached logs." | \
  mutt -s "$SCRIPTNAME [${DATE}] - $RC_INFO" \
       -a $ATTACHMENT \
       $RECIPIENT
}

# make sure we store the final iso:
store_iso() {
  if [ "$RC" = "0" ] ; then
     [ -d "$ISO_DIR" ] || mkdir "$ISO_DIR"
     mv $OUTPUT_DIR/grml_isos/$ISO_NAME $ISO_DIR
  fi
}

# allow clean exit:
bailout() {
  if [ "$RC" = "0" ] ; then
     rm -rf "$TMP_DIR" "$MUTT_HEADERS" "$OUTPUT_DIR"
  else
     rm -f "$MUTT_HEADERS"
     echo "building ISO failed, keeping build files [${OUTPUT_DIR} / ${TMP_DIR}]">&2
  fi

}

trap bailout 1 2 3 15

## END OF FILE #################################################################
