#!/bin/bash
################################################################################
# Purpose: hackish script to generate netboot package without booting the system
################################################################################

if [ $# -lt 2 ] ; then
  echo "Usage: $0 <chroot> <output_file>" >&2
  exit 1
fi

set -u
set -e

CHROOT="${1}"
OUTPUT_FILE="${2}"

if ! [ -f "${CHROOT}/etc/grml_version" ] ; then
  echo "Error: could not read ${CHROOT}/etc/grml_version" >&2
  exit 1
fi

GRML_VERSION="$(awk '{print $1"_"$2}' ${CHROOT}/etc/grml_version)"

if ! [ -r "${CHROOT}/usr/lib/syslinux/pxelinux.0" ] ; then
  echo "Error: /usr/lib/syslinux/pxelinux.0 not found. Please install syslinux[-common]." >&2
  exit 1
fi

OUTPUTDIR="$(mktemp -d)" || exit 1
WORKING_DIR="${OUTPUTDIR}/grml_netboot_package_${GRML_VERSION}/tftpboot/"
mkdir -p "$WORKING_DIR" || exit 2

cp "$CHROOT"/boot/vmlinuz-*    "$WORKING_DIR"/vmlinuz
cp "$CHROOT"/boot/initrd.img-* "$WORKING_DIR"/initrd.img
cp "$CHROOT"/usr/lib/syslinux/pxelinux.0 "${WORKING_DIR}/pxelinux.0"

if [ -r "$CHROOT"/usr/lib/syslinux/modules/bios/ldlinux.c32 ] ; then
  cp "$CHROOT"/usr/lib/syslinux/modules/bios/ldlinux.c32 "${WORKING_DIR}"/
fi

mkdir -p "${WORKING_DIR}/pxelinux.cfg"
cat > "${WORKING_DIR}/pxelinux.cfg/default" << EOF
default grml
label grml
  kernel vmlinuz
  append initrd=initrd.img root=/dev/nfs rw nfsroot=192.168.0.1:/live/image boot=live apm=power-off quiet nomce noprompt noeject vga=791 net.ifnames=0 
EOF

if tar -C "$OUTPUTDIR" -acf "${OUTPUT_FILE}" "grml_netboot_package_${GRML_VERSION}" ; then
  rm -rf "${OUTPUTDIR}"
  echo "Generated ${OUTPUT_FILE}"
fi

## END OF FILE #################################################################
