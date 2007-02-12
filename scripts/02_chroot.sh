# Filename:      02_chroot.sh
# Purpose:       build script for creating grml live-cd
# Authors:       grml-team (grml.org), (c) Michael Prokop <mika@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2.
# Latest change: Tue Feb 13 00:37:19 CET 2007
################################################################################

chroot_shell() {
  chroot "$TARGET" /bin/bash
}

chroot_exec() {
  chroot "$TARGET" /usr/bin/env -i HOME="/root" PATH="/usr/sbin:/usr/bin:/sbin:/bin" TERM="${TERM}" \
  DEBIAN_FRONTEND="${DEBCONF_FRONTEND}" DEBIAN_PRIORITY="${DEBCONF_PRIORITY}" ${1}
  return $?
}

patch_chroot() {
  case "${1}" in

       apply)
          debug "executing patch_chroot in apply mode"
          echo "grml-live" > "${TARGET}"/etc/debian_chroot
          [ -f "${TARGET}"/etc/hosts ] && cp "${TARGET}"/etc/hosts "$TARGET"/etc/hosts.orig
          [ -f /etc/hosts ]            && cp /etc/hosts "$TARGET"/etc/hosts
          [ -f "${TARGET}"/etc/resolv.conf ] && cp "${TARGET}"/etc/resolv.conf "$TARGET"/etc/resolv.conf.orig
          [ -f /etc/resolv.conf ]            && cp /etc/resolv.conf "$TARGET"/etc/resolv.conf
          # TODO: make sure to fix setup of grml-policy.rc.d
          cat > "${TARGET}"/usr/sbin/policy-rc.d <<EOF
#!/bin/sh
echo
echo "Information: policy-rc.d in action."
exit 101
EOF
          chmod 755 "${TARGET}"/usr/sbin/policy-rc.d
          ;;

       deapply)
          debug "executing patch_chroot in deapply mode"
          rm -f "${TARGET}"/etc/debian_chroot

          if [ -f "${TARGET}"/etc/hosts.orig ] ; then
             mv "${TARGET}"/etc/hosts.orig "$TARGET"/etc/hosts
          else
             rm -f "$TARGET"/etc/hosts
          fi

          # TODO: adjust for grml-policy.rc.d
          if [ -f "${TARGET}"/etc/resolv.conf.orig ] ; then
             mv "${TARGET}"/etc/resolv.conf.orig "$TARGET"/etc/resolv.conf
          else
             rm -f "$TARGET"/etc/resolv.conf
          fi

          rm -f "${TARGET}"/usr/sbin/policy-rc.d
          ;;
  esac
}

chroot_live_prepare() {
  debug "preparing grml-live directory in chroot"
  if [ -n "$SOURCES_LIST" ] ; then
     echo $SOURCES_LIST > "${TARGET}"/grml-live/files/sources.list
  fi

  cat > "${TARGET}"/grml-live/scripts/install_packages.sh << EOF
#!/bin/sh

if ! [ -f /etc/apt/grml.key ] ; then
   gpg --keyserver subkeys.pgp.net --recv-keys F61E2E7CECDEA787
   gpg --export F61E2E7CECDEA787 > /etc/apt/grml.key
   apt-key add /etc/apt/grml.key
fi

apt-get update
apt-get upgrade

EOF

  chmod 755 "${TARGET}"/grml-live/scripts/install_packages.sh
}

chroot_live_execute() {
  debug "executing grml-live script in chroot"
  chroot_exec /grml-live/scripts/install_packages.sh
}

## END OF FILE #################################################################
# vim: ai tw=80 ft=sh expandtab
