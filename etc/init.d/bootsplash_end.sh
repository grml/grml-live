#!/bin/sh
# Filename:      bootsplash_end.sh
# Purpose:       last stage of textbased bootsplash
# Authors:       grml-team (grml.org), (c) Michael Prokop <mika@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2.
# Latest change: Don Sep 20 15:56:56 CEST 2007 [mika]
################################################################################

. /etc/grml/autoconfig.functions

if checkbootparam "textsplash" || checkbootparam "tsplash"; then
  /usr/bin/grml-bootsplash "||||||||||||">/dev/tty14
  chvt 1
  deallocvt 14
fi

## END OF FILE #################################################################
