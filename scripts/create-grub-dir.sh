#!/bin/bash
# Filename:      create-grub-dir.sh
# Purpose:       generate core.img and according files for templates/boot/grub/
# Authors:       grml-team (grml.org), (c) Michael Prokop <mika@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2 or any later version.
# Latest change: Thu Mar 11 14:25:15 CET 2010 [mika]
################################################################################
# This script is very hackish due to the way the grub directory has to be
# generated. :-/ The script is meant to be executed on a Debian system that
# matches the grub version, otherwise the execution of grub-mkimage *might* fail.
# So if you want to use a recent Grub version make sure you execute this script
# on an up2date Debian/unstable system.
################################################################################

set -e

if [ -z "$1" ] ; then
  echo "Usage: $0 <grub-version>">&2
  echo "Usage example: $0 1.98-1">&2
  exit 1
fi

if [ -d grub ] ; then
  echo "Directory 'grub' exists in current working directory already, will not continue.">&2
  exit 1
fi

GRUB="$1"
oldpwd=$(pwd)

ARCH=$(dpkg --print-architecture)

if ! [ -f "grub-pc_${GRUB}_${ARCH}.deb" ] || ! [ -f "grub-common_${GRUB}_${ARCH}.deb" ]  ; then
  wget http://cdn.debian.net/debian/pool/main/g/grub2/grub-pc_"${GRUB}"_${ARCH}.deb
  wget http://cdn.debian.net/debian/pool/main/g/grub2/grub-common_"${GRUB}"_${ARCH}.deb
fi

if ! [ -f "grub-pc_${GRUB}_${ARCH}.deb" ] || ! [ -f "grub-common_${GRUB}_${ARCH}.deb" ]  ; then
  echo "Error reading grub files version $GRUB - exiting.">&2
  exit 1
fi

GRUBDIR=$(mktemp -d)
echo "Using temporary directory $GRUBDIR"
cd "$GRUBDIR"

mkdir -p grub

ar x "${oldpwd}"/"grub-pc_${GRUB}_${ARCH}.deb"
tar xzf data.tar.gz
ar x "${oldpwd}"/"grub-common_${GRUB}_${ARCH}.deb"
tar xzf data.tar.gz

if ./usr/bin/grub-mkimage --help | grep -q -- --format ; then
  ./usr/bin/grub-mkimage -d usr/lib/grub/*-pc -o core.img biosdisk iso9660 --format=i386-pc
else
  ./usr/bin/grub-mkimage -d usr/lib/grub/*-pc -o core.img biosdisk iso9660
fi

for a in usr/lib/grub/*-pc/{*.mod,efiemu??.o,command.lst,moddep.lst,fs.lst,handler.lst,parttool.lst}; do \
  [[ -e $a ]] && cp $a grub/
done

mv core.img grub/

cd "$oldpwd"
mv "${GRUBDIR}"/grub .
rm -rf "$GRUBDIR"

echo "Generated new grub boot directory 'grub'."

## END OF FILE #################################################################
