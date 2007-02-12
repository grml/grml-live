# Filename:      functions.sh
# Purpose:       helper functions for use within grml-live
# Authors:       grml-team (grml.org), (c) Michael Prokop <mika@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2.
# Latest change: Thu Feb 08 22:35:46 CET 2007
################################################################################

bailout(){
  [ -n "$1" ] && EXIT="$1" || EXIT="1"
  [ -n "$2" ] && echo "$2">&2
  exit "$EXIT"
}

usage() {
  print "
  $0 ....
"
}

debug() {
  if [[ -n "$DEBUG" ]] ; then
     einfo "grml-live: $*"
     [[ -n "$DEBUG_SYSLOG" ]] && [ -x /usr/bin/logger ] && logger -t grml-live-info "$*"
  else
     return 0 # do nothing
  fi
}

debug_warn() {
  if [[ -n "$DEBUG" ]] ; then
     ewarn "grml-live: $*"
     [[ -n "$DEBUG_SYSLOG" ]] && [ -x /usr/bin/logger ] && logger -t grml-live-warn "$*"
  else
     return 0 # do nothing
  fi
}

debug_error() {
  if [[ -n "$DEBUG" ]] ; then
     eerror "grml-live: $*"
     [[ -n "$DEBUG_SYSLOG" ]] && [ -x /usr/bin/logger ] && logger -t grml-live-error "$*"
  else
     return 0 # do nothing
  fi
}

chroot_exec()
{
  [ -n "$TARGET" ] || bailout 1 "\$TARGET unset, can not chroot_exec"
  [ -n "$1" ] || bailout 1 "Error executing chroot_exec. Usage: chroot_exec <command>"
  chroot "$TARGET" "$1"
}

## END OF FILE #################################################################
