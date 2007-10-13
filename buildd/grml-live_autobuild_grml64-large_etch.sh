#!/bin/sh

set -u

PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/bin/X11

# configuration:
DATE=$(date +%Y%m%d)
STORAGE=/grml-live/
OUTPUT_DIR="${STORAGE}/grml-live_${DATE}.$$"
TMP_DIR=$(mktemp -d)
MUTT_HEADERS=$(mktemp)
ATTACHMENT=$TMP_DIR/grml-live-logs_$DATE.tar.gz
RECIPIENT=grml-live@ml.grml.org
ISO_NAME=grml64_etch_$DATE.iso
ISO_DIR=/grml-live/grml-isos
[ -n "$TMP_DIR" ] || exit 10
[ -n "$MUTT_HEADERS" ] || exit 20
echo "my_hdr From: grml-live autobuild daemon <grml-live@grml.org>" > $MUTT_HEADERS

# execute grml-live:
grml-live -F -s etch -c GRMLBASE,GRML_FULL,LATEX_CLEANUP,AMD64 -o $OUTPUT_DIR \
          -g grml64 -v $DATE -r grml-live-autobuild -i $ISO_NAME          \
	  1>${TMP_DIR}/stdout 2>${TMP_DIR}/stderr ; RC=$?

# create log archive:
tar zcf $ATTACHMENT /var/log/fai/dirinstall/grml 1>/dev/null

if ! [ -f "$OUTPUT_DIR/grml_isos/$ISO_NAME" ] ; then
   ISO_DETAILS="There was an error creating $ISO_NAME"
else
   ISO_DETAILS=$(ls -lh $OUTPUT_DIR/grml_isos/$ISO_NAME)
fi

# send status mail:
echo -en "Automatically generated mail by grml-live_autobuild_grml-large_etch.sh

$ISO_DETAILS

Return code of grml-live run was: $RC

Find details in the attached logs." | \
mutt -s "grml-live_autobuild_grml64-large_etch.sh [${DATE}] - $RC" \
     -a ${TMP_DIR}/stdout \
     -a ${TMP_DIR}/stderr \
     -a $ATTACHMENT \
     $RECIPIENT

# make sure we store the final iso:
[ -d "$ISO_DIR" ] || mkdir "$ISO_DIR"
mv $OUTPUT_DIR/grml_isos/$ISO_NAME $ISO_DIR

rm -rf "$TMP_DIR" "$MUTT_HEADERS" "$OUTPUT_DIR"
