#!/bin/sh
[ -n "$KERNEL" ] || KERNEL='2.6.20-grml'
for s in $(find /lib/modules/$KERNEL/kernel/drivers/scsi -name *.ko); do
 # DEP=$(modinfo $s|grep '^depends:'|echo $(cut -d' ' -f2-))
 DEP=$(modinfo $s|grep '^depends:'|cut -d' ' -f2-)
 case $DEP in
  *pcmcia*)
   ;;
  *)
   modinfo $s|grep '^alias:'|grep pci|while read a; do
    echo $a $DEP $(basename $s|sed 's/\.ko//')|cut -f3- -d:
   done
   ;;
 esac
done|sort|uniq 
