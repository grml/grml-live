#!/bin/sh
# Filename:      bootsplash_start.sh
# Purpose:       first stage of textbased bootsplash
# Authors:       grml-team (grml.org), (c) Michael Prokop <mika@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2.
# Latest change: Don Sep 20 15:56:54 CEST 2007 [mika]
################################################################################

. /etc/grml/autoconfig.functions

if checkbootparam "textsplash" || checkbootparam "tsplash"; then
  # make sure console font is set at this stage already
  consolechars -f Lat15-Terminus16
  chvt 14
  /usr/bin/grml-bootsplash "">/dev/tty14
fi

## END OF FILE #################################################################
