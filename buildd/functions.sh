#!/bin/sh
# Filename:      /usr/share/grml-live/buildd/functions.sh
# Purpose:       main function file for grml-live buildd
# Authors:       grml-team (grml.org), (c) Michael Prokop <mika@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2 or any later version.
# Latest change: Sun Dec 09 18:38:26 CET 2007 [mika]
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
[ -n "$FROM" ]          || FROM=root@localhost

if [ -n "$LOGFILE" ] ; then
   GRML_LOGFILE="$LOGFILE"
else
   [ -n "$GRML_LOGFILE" ]  || GRML_LOGFILE=/var/log/grml-live.log
fi

[ -n "$FAI_LOGFILES" ]  || FAI_LOGFILES=/var/log/fai/grml/last

echo "my_hdr From: grml-live autobuild daemon <$FROM>" > $MUTT_HEADERS

# execute grml-live:
grml_live_run() {
  if ! [ "$FORCE_REBUILD" = "1" ] ; then
     if [ -f "$ISO_DIR/$ISO_NAME" ] ; then
        echo "$ISO_DIR/$ISO_NAME exists already. Nothing to be done, exiting."
        exit 0
     fi
  fi

  grml-live -F $* $GRML_LIVE_ARCH -s $SUITE -c $CLASSES -o $OUTPUT_DIR \
            -g $NAME -v $DATE -r grml-live-autobuild -i $ISO_NAME \
            1>/var/log/grml-buildd.stdout \
            2>/var/log/grml-buildd.stderr ; RC=$?

  if [ "$RC" = "0" ] ; then
     RC_INFO=success
  else
     RC_INFO=error
  fi
}

# create log archive:
create_logs() {
  ( cd / && tar zcf $ATTACHMENT $FAI_LOGFILES $GRML_LOGFILE 1>/dev/null )
}

# store logs on remote server:
upload_logs() {
  [ -n "$RSYNC_MIRROR" ] || return 1
  umask 002
  rsync --exclude dmesg.log --times --partial --copy-links -az --quiet /var/log/grml-buildd.* \
  $FAI_LOGFILES $GRML_LOGFILE $RSYNC_MIRROR/logs/"${NAME}_${DATE}"/
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
  # attach logs only if we have some:
  [ -r "$ATTACHMENT" ] && MUTT_ATTACH="-a $ATTACHMENT" || MUTT_ATTACH=''

  echo -en "Automatically generated mail by $SCRIPTNAME

$ISO_DETAILS

Return code of grml-live run was: $RC

$(grep -A2 'Executed grml-live' $GRML_LOGFILE || echo "* executed grml-live command line not available")

$(grep -A2 'Executed FAI' $GRML_LOGFILE || echo "* executed FAI command line not available")

The following errors have been noticed (several might be warnings only):

$(grep -i error $FAI_LOGFILES/* /var/log/grml-buildd.std* | grep -ve liberror -ve libgpg-error || echo "* nothing")

The following warnings have been noticed:

$(grep -i warn $FAI_LOGFILES/* /var/log/grml-buildd.std* || echo "* nothing")

There following dependency problems have been noticed:

$(grep -i "Not Installed" $FAI_LOGFILES/software.log || echo "* nothing")

The following packages could not be installed:

$(grep -i "Couldn't find.*package" $FAI_LOGFILES/software.log | sed 's/\(.*\)"\(.*\)"\(.*\)/\2/' | sort -u || echo "* nothing")

EOF " | \
  mutt -s "$SCRIPTNAME [${DATE}] - $RC_INFO" $MUTT_ATTACH "$RECIPIENT"
}

# make sure we store the final iso:
store_iso() {
  if [ "$RC" = "0" ] ; then
     [ -d "$ISO_DIR" ] || mkdir "$ISO_DIR"
     mv "${OUTPUT_DIR}/grml_isos/${ISO_NAME}" "$ISO_DIR"
     if [ -r "${OUTPUT_DIR}/grml_isos/${ISO_NAME}.md5" ] ; then
        mv   "${OUTPUT_DIR}/grml_isos/${ISO_NAME}.md5" "${ISO_DIR}"
     fi
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
