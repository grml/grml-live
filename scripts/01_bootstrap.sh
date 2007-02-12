# Filename:      01_bootstrap.sh
# Purpose:       build script for creating grml live-cd
# Authors:       grml-team (grml.org), (c) Michael Prokop <mika@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2.
# Latest change: Tue Feb 13 00:13:24 CET 2007
################################################################################

# main execution
bootstrap() {
  debug "executing bootstrap" ; 

  # create main grml-live directory within chroot
  if ! [ -d "${TARGET}/grml-live/" ] ; then
     debug "bootstrap: creating ${TARGET}/grml-live/"
     mkdir "${TARGET}/grml-live/"
     mkdir "${TARGET}/grml-live/scripts/"
     mkdir "${TARGET}/grml-live/files/"
  fi

  # check whether chroot exists already 
  if [ -f "${TARGET}/grml-live/bootstrap" ] ; then
     debug_warn "chroot exists already, skipping execution of $DEBOOTSTRAP and continuing"
  else
     $DEBOOTSTRAP --arch $ARCH $RELEASE $TARGET $MIRROR && touch "${TARGET}/grml-live/bootstrap"
  fi
}

## END OF FILE #################################################################
# vim: ai tw=80 ft=sh expandtab
