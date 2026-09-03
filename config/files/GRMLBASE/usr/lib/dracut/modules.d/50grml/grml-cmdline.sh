#!/bin/sh
#
# This file was deployed via grml-live's
# ${GRML_FAI_CONFIG}/scripts/GRMLBASE/80-initramfs script, using
# ${GRML_FAI_CONFIG}/files/GRMLBASE/usr/lib/dracut/modules.d/50grml/grml-cmdline.sh
#
# Filename:      /usr/lib/dracut/modules.d/50grml/grml-cmdline.sh
# Purpose:       Early boot branding
# Authors:       grml-team (grml.org),
#                (c) Michael Prokop <mika@grml.org>,
#                Chris Hofstaedtler <ch@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2 or any later version.
################################################################################
# shellcheck shell=ash

# shellcheck disable=SC1091
. /lib/dracut-lib.sh

if getargbool 1 "nocolor" ; then
  # shellcheck disable=SC2034
  {
  # ANSI COLORS
  ESC="$(printf '\033')"
  # Normal color
  NORMAL="${ESC}[0;39m"
  # RED: Failure or error message
  RED="${ESC}[1;31m"
  # GREEN: Success message
  GREEN="${ESC}[1;32m"
  # YELLOW: Descriptions
  YELLOW="${ESC}[1;33m"
  # BLUE: System messages
  BLUE="${ESC}[1;34m"
  # MAGENTA: Found devices or drivers
  MAGENTA="${ESC}[1;35m"
  # CYAN: Questions
  CYAN="${ESC}[1;36m"
  # BOLD WHITE: Hint
  WHITE="${ESC}[1;37m"
  }
else
  # shellcheck disable=SC2034
  {
  NORMAL=""
  RED=""
  GREEN=""
  YELLOW=""
  BLUE=""
  MAGENTA=""
  CYAN=""
  WHITE=""
  }
fi

# shellcheck disable=SC1091
. /etc/os-release

if [ "$ID" = "grml" ] ; then
SPLASH="
${YELLOW}          ____              _
${YELLOW}         / ___| _ __ _____ | |
${YELLOW}        | |  _ | / /|     || |
${YELLOW}        | |_| ||  / | | | || |
${YELLOW}         \____||_|  |_|_|_||_|

${WHITE}  Grml Live Linux - https://grml.org/${NORMAL}"
else
SPLASH="
${RED}  $PRETTY_NAME

${WHITE}  based on grml.org.

${NORMAL}"
fi

echo "

${WHITE}  Welcome to

$SPLASH

${GREEN}  $PRETTY_NAME
${NORMAL}" > /dev/console
