#!/bin/bash

EXPECTED_LABEL=''
TMPNAME=$(mktemp)

export_var() {
    echo "$1"="$2" >> "$TMPNAME"
}

blkid() {
	echo > "$TMPNAME"
	while [ -n "$1" ] ; do
	  case "$1" in
		LABEL*)
		assertEquals "unexpected label value"  "${EXPECTED_LABEL:-GRMLCFG}" "${1/LABEL=/}" >&2
		# shellcheck disable=SC2154
		{
			export_var __shunit_testSuccess "$__shunit_testSuccess"
			export_var __shunit_assertsFailed "$__shunit_assertsFailed"
			export_var __shunit_assertsTotal "$__shunit_assertsTotal"
		}
	  esac
	  shift
	done
}

test_grmlcfg() {
    # shellcheck disable=SC2034  # used by autoconfig.functions
	CONFIG_MYCONFIG='yes'
	# shellcheck disable=SC2034  # used by autoconfig.functions
	INSTALLED=""

	EXPECTED_LABEL=''
	CMDLINE=""
	config_finddcsdir >/dev/null
	# shellcheck disable=SC1090
	. "$TMPNAME"

	EXPECTED_LABEL='test1'
	# shellcheck disable=SC2034  # used by autoconfig.functions
	CMDLINE="autoconfig=$EXPECTED_LABEL"
	config_finddcsdir >/dev/null
	# shellcheck disable=SC1090
	. "$TMPNAME"
}


tearDown() {
	rm "$TMPNAME"
}

. ./common_tests
# shellcheck source=/dev/null
. shunit2
