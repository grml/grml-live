# Filename:      functions.sh
# Purpose:       helper functions for use within grml-live
# Authors:       grml-team (grml.org), (c) Michael Prokop <mika@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2.
# Latest change: Thu Feb 08 22:35:46 CET 2007
################################################################################

bailout(){
  [ -n "$1" ] && EXIT="$1" || EXIT="1"
  exit "$EXIT"
}

usage() {
  print "
  $0 ....
"
}

debug() {
  if [[ -n "$DEBUG" ]] ; then
     print "grml-live: $*"
     [[ -n "$DEBUG_SYSLOG" ]] && [ -x /usr/bin/logger ] && logger -t grml-live "$*"
  else
     return 0 # do nothing
  fi
}

cmdline_options () {
        while true
        do
                case "${1}" in
                        (-r|--root) LIVE_ROOT="${2}"
                                shift 2 ;;
                        (-v|--version) usage
                                exit 1 ;;
                        (--) shift
                                break ;;
                        (*) exit 0 ;;
                esac
        done
}
chroot_exec()
{
;
}

## END OF FILE #################################################################
