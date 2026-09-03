#!/bin/bash
#
# This file was deployed via grml-live's
# ${GRML_FAI_CONFIG}/scripts/GRMLBASE/80-initramfs script, using
# ${GRML_FAI_CONFIG}/files/GRMLBASE/usr/lib/dracut/modules.d/50grml/module-setup.sh
#
# Filename:      /usr/lib/dracut/modules.d/50grml/module-setup.sh
# Purpose:       Install grml dracut module files
# Authors:       grml-team (grml.org),
#                (c) Michael Prokop <mika@grml.org>,
#                Chris Hofstaedtler <ch@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2 or any later version.
################################################################################
# shellcheck shell=bash

# called by dracut
install() {
    # these are set by dracut, but shellcheck does not know that.
    moddir=${moddir:?}

    inst_simple /etc/grml_version

    inst_hook cmdline "01" "$moddir/grml-cmdline.sh"
    inst_hook emergency "01" "$moddir"/grml-emergency.sh
}
