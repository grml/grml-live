#!/bin/sh
# Filename:      .xinitrc
# Purpose:       specify details for xserver
# Authors:       grml-team (grml.org), (c) Michael Prokop <mika@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2.
################################################################################

# is something goes wrong fall back to plain x-terminal-emulator:
#  failsafe="x-terminal-emulator -ls -T failsafe -geometry 80x24-0-0"
#  trap "exec $failsafe" EXIT 1 2 13 15

# set wallpaper
# wmsetbg -t /usr/share/grml/desktop.png &
  if [ -x /usr/bin/Esetroot ] ; then
     [ -r /usr/share/grml/desktop.jpg ] && Esetroot -scale /usr/share/grml/desktop.jpg &
  fi

# print info text
  if [ -x /usr/bin/osd_cat ] ; then
     echo "Starting X window system and loading window manager..." | \
     osd_cat -c white -A center -p middle -f "-misc-fixed-medium-r-normal-*-*-150-*-*-c-*-iso8859-15" &
  fi

# add at least one entry to xauth
#  xauth add $DISPLAY MIT-MAGIC-COOKIE-1 `mcookie`

# set default cursor
  xsetroot -cursor_name left_ptr

## set mouse speed behaviour:
# fast:
# xset m 4 2
# normal:
  xset m 2 5
# slow:
# xset m 1 1

# other settings:
# xset m 20/10 4

# disable screensaver and dpms:
# xset s off
# xset -dpms

# xresources
  [ -r $HOME/.Xresources ] && xrdb -merge $HOME/.Xresources

# keybindings
  if ! [ -r /etc/sysconfig/keyboard ] ; then
     [ -r $HOME/.Xmodmap ] && xmodmap $HOME/.Xmodmap || setxkbmap us
  else
     . /etc/sysconfig/keyboard
     if [ $XKEYBOARD == "us" ] ; then
        [ -r $HOME/.Xmodmap ] && xmodmap $HOME/.Xmodmap
     else
        if [ -n "$XKEYMODEL" ] ; then
           setxkbmap -model "$XKEYMODEL" -layout "$XKEYBOARD"
        else
           setxkbmap "$XKEYBOARD"
        fi
     fi
  fi

# mouse for lefty:
# xmodmap -e "pointer = 3 2 1"
# mouse for right hander:
# xmodmap -e "pointer = 1 2 3"

# start browser with startpage.html, but only in live-cd mode
  [ -r /etc/grml_cd ] && grml-info &

# default entry, use e.g. 'grml-x windowmanager' for changing or just adjust manually
  exec /usr/bin/x-window-manager

## END OF FILE #################################################################
