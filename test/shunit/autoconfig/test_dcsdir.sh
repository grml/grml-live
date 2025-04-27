#!/bin/zsh


test_finddcsdir() {
    CMDLINE=''
    INSTALLED=''

    EXPECTED_PATH='/run/live/medium'

    config_finddcsdir &>/dev/null

    assertEquals 'dcsdir is wrong' ${EXPECTED_PATH} ${DCSDIR}

}

. ./common_tests $0
