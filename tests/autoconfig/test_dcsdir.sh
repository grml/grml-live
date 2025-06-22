#!/bin/bash

test_finddcsdir() {
    # shellcheck disable=SC2034  # used by autoconfig.functions
    CMDLINE=''
    # shellcheck disable=SC2034  # used by autoconfig.functions
    INSTALLED=''

    # Normally LIVECD_PATH is set by autoconfig.functions, but the
    # directory does not exist in non-live systems.
    LIVECD_PATH='/tmp'
    EXPECTED_PATH='/tmp'

    config_finddcsdir &>/dev/null

    assertEquals 'dcsdir is wrong' "${EXPECTED_PATH}" "${DCSDIR}"
}

. ./common_tests
# shellcheck source=/dev/null
. shunit2
