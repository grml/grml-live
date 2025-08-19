#!/bin/sh
# Filename:      ~/.xinitrc
# Purpose:       main configuration file of X startup
# Authors:       grml-team (grml.org), (c) Michael Prokop <mika@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2 or any later version.
################################################################################

# $distri is supposed to be set already
distri=${distri:-}

# configuration: by default all scripts from ~/.xinitrc.d are executed,
# but it's possible to configure this through a configuration file
if [ -r "$HOME/.config/${distri}/xinitrc" ] ; then
  # shellcheck source=/dev/null
  . "$HOME/.config/${distri}/xinitrc"
elif [ -r "$HOME/.config/grml/xinitrc" ] ; then
  # shellcheck source=/dev/null
  . "$HOME/.config/grml/xinitrc"
fi

# execute all existing scripts
for f in ~/.xinitrc.d/* ; do
  "$f"
done

# default entry, use e.g. 'grml-x windowmanager' for changing or just adjust manually
exec /usr/bin/x-window-manager

## END OF FILE #################################################################
