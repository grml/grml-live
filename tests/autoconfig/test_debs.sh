#!/bin/bash
# This test does not use shunit2 as shunit2 requires shwordsplit
# But shwordsplit is not enabled per default in zsh and needs to be
# taken care of in autoconfig.functions.

EXPECTED_COUNT=4
dpkg() {
    # remove the -i parameter
    shift

    echo "dpkg params: $*"

    if [ $# -ne $EXPECTED_COUNT ] ; then
        echo "wrong parameter count for dpkg, was $# expected $EXPECTED_COUNT" >&2
        exit 1
    fi
}

test_debs() {
    . ../../config/files/GRMLBASE/usr/share/grml-autoconfig/autoconfig.functions || exit 1

    # shellcheck disable=SC2034  # used by autoconfig.functions
    CMDLINE='debs'
    # shellcheck disable=SC2034  # used by autoconfig.functions
    INSTALLED=''

    TMPDIR=$(mktemp -d)
    DCSDIR="$TMPDIR"
    DEB_DIR="$DCSDIR"/debs
    mkdir -p "$DEB_DIR"
    for ((i=1; i <= "${EXPECTED_COUNT}"; i++)); do
        touch "$DEB_DIR"/${i}.deb
    done

    einfo() { echo "$*"; }
    eend() { echo ; }
    config_debs

    rm -rf "$TMPDIR"
}

test_debs
