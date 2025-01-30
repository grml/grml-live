#!/bin/zsh
# This test does not use shunit2 as shunit2 requires shwordsplit
# But shwordsplit is not enabled per default in zsh and needs to be
# taken care of in autoconfig.functions.

EXPECTED_COUNT=4
dpkg() {
    # remove the -i parameter
    shift

    if [ $# -ne $EXPECTED_COUNT ] ; then
        echo "wrong parameter count for dpkg, was $# expected $EXPECTED_COUNT" >&2
        exit 1
    fi
}

test_debs() {
    . ../autoconfig.functions || exit 1
    CMDLINE='debs'
    INSTALLED=''

    TMPDIR=$(mktemp -d)
    DCSDIR="$TMPDIR"
    DEB_DIR="$DCSDIR"/debs
    mkdir -p "$DEB_DIR"
    touch "$DEB_DIR"/{1..$EXPECTED_COUNT}.deb

    einfo() { echo "$*"; }
    eend() { echo ; }
    config_debs

    rm -rf "$TMPDIR"
}

test_debs
