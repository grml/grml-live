#!/bin/bash

MIRROR_DIRECTORY=$1
if [ -z "$MIRROR_DIRECTORY" ] ; then
  echo "Usage: jenkins-link_latest.sh path_to_public_directory flavour1 ... flavourN" >&2
  exit 1
fi
shift

FLAVOURS=$*

JOBS=/var/lib/jenkins/jobs

cd $MIRROR_DIRECTORY || exit 1
for f in $FLAVOURS; do
  [ -d $JOBS/$f/builds ] || continue
  [ -d ./$f ] && rm -r ./$f
  mkdir $f
  for buildpath in $JOBS/$f/builds/*_*; do
    build=$(basename $buildpath)
    mkdir $f/$build
    for isofile in $buildpath/archive/grml_isos/*; do
      [ -e $isofile ] && ln -s $isofile $f/$build/
    done
    [ -d $buildpath/archive/grml_logs ] && ln -s $buildpath/archive/grml_logs $f/$build/logs
  done
  latest=$(basename $(readlink $JOBS/$f/lastSuccessful))
  mkdir ${f}/latest
  if [ -e $f/$latest/*.iso ]; then
    latestname=$(basename ${f}/$latest/*.iso)
    ln -s ../$latest/${latestname} ${f}/latest/${f}_latest.iso
    ln -s ../$latest/${latestname}.md5 ${f}/latest/${f}_latest.iso.md5
    ln -s ../$latest/${latestname}.sha1 ${f}/latest/${f}_latest.iso.sha1
  fi
done
