#!/bin/sh
# Filename:      bootsplash_start.sh
# Purpose:       first stage of textbased bootsplash
# Authors:       grml-team (grml.org), (c) Michael Prokop <mika@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2.
# Latest change: Fre Aug 04 12:20:36 CEST 2006 [mika]
################################################################################

. /etc/grml/autoconfig.functions

if checkbootparam "splash" ; then
# make sure console font is set at this stage already
  consolechars -f Lat15-Terminus16
  chvt 7
  /usr/bin/grml-bootsplash "">/dev/tty7
fi

## END OF FILE #################################################################
