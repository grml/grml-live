#!/bin/zsh


test_finddcsdir() {
    CMDLINE=''
    INSTALLED=''

    EXPECTED_PATH='/live/image'

    config_finddcsdir &>/dev/null

    assertEquals 'dcsdir is wrong' ${EXPECTED_PATH} ${DCSDIR}

}

. ./common_tests $0
