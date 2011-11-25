#!/bin/bash
set -e
. /etc/grml/grml-buildd.conf

if [ -z "$MIRROR_DIRECTORY" ] ; then
  echo "Error: \$MIRROR_DIRECTORY is not set. Exiting." >&2
  exit 1
fi

if [ -z "$FLAVOURS" ] ; then
  echo "Error: \$FLAVOURS is not set. Exiting." >&2
  exit 2
fi

cd $MIRROR_DIRECTORY || exit 1
for f in $FLAVOURS; do
  rm -r ./$f
  rm ./$f*.iso*
  mkdir $f
  for buildpath in /var/lib/jenkins/jobs/$f/builds/*_*; do
    build=$(basename $buildpath)
    mkdir $f/$build
    for isofile in $buildpath/archive/iso/*; do
      ln -s $isofile $f/$build/
    done
    ln -s $buildpath/archive/logs $f/$build/logs
  done
  latest=$(basename $(readlink /var/lib/jenkins/jobs/$f/lastStable))
  ln -s $f/$latest/*.iso ${f}_latest.iso
  ln -s $f/$latest/*.iso.md5 ${f}_latest.iso.md5
  ln -s $f/$latest/*.iso.sha1 ${f}_latest.iso.sha1
done

