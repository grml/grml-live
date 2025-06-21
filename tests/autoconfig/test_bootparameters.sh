#!/bin/bash

test_checkbootparam() {
    CMDLINE='foo=dingens bar foobar=blub'

    checkbootparam foobar
    retval=$?
    assertEquals 'wrong retval for bootparam foobar' 0 "${retval}"

    checkbootparam bar
    retval=$?
    assertEquals 'wrong retval for bootparam bar' 0 "${retval}"

    checkbootparam foo
    retval=$?
    assertEquals 'wrong retval for bootparam foo' 0 "${retval}"

    checkbootparam dingens
    retval=$?
    assertEquals 'wrong retval for non-existing bootparam dingens' 1 "${retval}"

    checkbootparam oops
    retval=$?
    assertEquals 'wrong retval for non-existing bootparam oops' 1 "${retval}"
}

test_getbootparam() {
    CMDLINE='test=dingens tester foo=dingens foobar=blub'

    value=$(getbootparam foobar)
    retval=$?
    assertEquals 'unexpected value for botparam foobar' 'blub' "${value}"
    assertEquals 'unexpected retval' '0' "${retval}"

    value=$(getbootparam foo)
    retval=$?
    assertEquals 'unexpected value for bootparam foo' 'dingens' "${value}"
    assertEquals 'unexpected retval' 0 "${retval}"

    value=$(getbootparam test)
    retval=$?
    assertEquals 'unexpected value for bootparam test' 'dingens' "${value}"
    assertEquals 'unexpected retval' 0 "${retval}"

    value=$(getbootparam tester)
    retval=$?
    assertTrue 'expected empty string' "[ -z ${value} ]"
    assertEquals 'unexpected retval' 1 "${retval}"
}

. ./common_tests
# shellcheck source=/dev/null
. shunit2
