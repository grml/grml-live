#!/bin/sh
# Filename:      bootsplash_end.sh
# Purpose:       last stage of textbased bootsplash
# Authors:       grml-team (grml.org), (c) Michael Prokop <mika@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2.
# Latest change: Fre Aug 04 12:20:30 CEST 2006 [mika]
################################################################################

. /etc/grml/autoconfig.functions

if checkbootparam "splash" ; then
  /usr/bin/grml-bootsplash "||||||||||||">/dev/tty7
  chvt 1
  deallocvt 7
fi

## END OF FILE #################################################################
