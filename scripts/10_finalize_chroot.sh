# Filename:      10_finalize_chroot.sh
# Purpose:       build script for creating grml live-cd
# Authors:       grml-team (grml.org), (c) Michael Prokop <mika@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2.
# Latest change: Mon Feb 12 23:24:17 CET 2007
################################################################################

# main execution
chroot_finalize() {
  if [ -f "${TARGET}/etc/apt/sources.list.grml" ] ; then
     chroot_exec "( cd /etc/apt/ ; ln -s sources.list.grml sources.list )"
  fi
}

## END OF FILE #################################################################
# vim: ai tw=80 ft=sh expandtab
