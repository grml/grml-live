#!/bin/bash
# Filename:      create-grub-dir.sh
# Purpose:       generate core.img and according files for templates/boot/grub/
# Authors:       grml-team (grml.org), (c) Michael Prokop <mika@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2 or any later version.
# Latest change: Thu Mar 11 14:25:15 CET 2010 [mika]
################################################################################

set -e

if [ -z "$1" ] ; then
  echo "Usage: $0 <grub_package.deb>">&2
  echo "Usage example: $0 grub-pc_1.98-1_i386.deb">&2
  exit 1
fi

if [ -d grub ] ; then
  echo "Directory 'grub' exists in current working directory already, will not continue.">&2
  exit 1
fi

GRUB="$1"
oldpwd=$(pwd)

if ! [ -f "$GRUB" ] ; then
  wget http://ftp.de.debian.org/debian/pool/main/g/grub2/"$GRUB"
fi

if ! [ -f "$GRUB" ] ; then
  echo "Error reading $GRUB - exiting.">&2
  exit 1
fi

GRUBDIR=$(mktemp -d)
cd "$GRUBDIR"

mkdir -p grub

ar x "${oldpwd}"/"$GRUB"
tar xzf data.tar.gz
./usr/bin/grub-mkimage -d usr/lib/grub/i386-pc -o core.img biosdisk iso9660

for a in usr/lib/grub/i386-pc/{*.mod,efiemu??.o,command.lst,moddep.lst,fs.lst,handler.lst,parttool.lst}; do \
  [[ -e $a ]] && cp $a grub/
done

mv core.img grub/

cd "$oldpwd"
mv "${GRUBDIR}"/grub .
rm -rf "$GRUBDIR"

echo "Generated new grub boot directory 'grub'."

## END OF FILE #################################################################
