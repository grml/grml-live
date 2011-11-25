#!/bin/bash
. /etc/grml/grml-buildd.conf

if [ -z "$MIRROR_DIRECTORY" ] ; then
  echo "Error: \$MIRROR_DIRECTORY is not set. Exiting." >&2
  exit 1
fi

if [ -z "$FLAVOURS" ] ; then
  echo "Error: \$FLAVOURS is not set. Exiting." >&2
  exit 2
fi

JOBS=/var/lib/jenkins/jobs

cd $MIRROR_DIRECTORY || exit 1
for f in $FLAVOURS; do
  [ -d $JOBS/$f/builds ] || continue
  [ -d ./$f ] && rm -r ./$f
  for link in ./$f*.iso*; do rm $link; done
  mkdir $f
  for buildpath in $JOBS/$f/builds/*_*; do
    build=$(basename $buildpath)
    mkdir $f/$build
    for isofile in $buildpath/archive/grml_isos/*; do
      [ -e $isofile ] && ln -s $isofile $f/$build/
    done
    [ -d $buildpath/archive/grml_logs ] && ln -s $buildpath/archive/grml_logs $f/$build/logs
  done
  latest=$(basename $(readlink $JOBS/$f/lastStable))
  if [ -e $f/$latest/*.iso ]; then
    ln -s $f/$latest/*.iso ${f}_latest.iso
    ln -s $f/$latest/*.iso.md5 ${f}_latest.iso.md5
    ln -s $f/$latest/*.iso.sha1 ${f}_latest.iso.sha1
  fi
done
