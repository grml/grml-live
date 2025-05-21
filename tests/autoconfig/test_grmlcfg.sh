#!/bin/zsh

EXPECTED_LABEL=''
TMPNAME=$(mktemp)

export_var() {
	echo $1=$(eval echo $"$1") >> $TMPNAME
}

blkid() {
	echo > "$TMPNAME"
	while [ -n "$1" ] ; do
	  case "$1" in
		LABEL*)
		assertEquals "unexpected label value"  "${EXPECTED_LABEL:-GRMLCFG}" "${1/LABEL=/}" >&2
		export_var __shunit_testSuccess
		export_var __shunit_assertsFailed
		export_var __shunit_assertsTotal
	  esac
	  shift
	done
}

test_grmlcfg() {
	CONFIG_MYCONFIG='yes'
	INSTALLED=""

	EXPECTED_LABEL=''
	CMDLINE=""
	config_finddcsdir >/dev/null
	. "$TMPNAME"

	EXPECTED_LABEL='test1'
	CMDLINE="autoconfig=$EXPECTED_LABEL"
	config_finddcsdir >/dev/null
	. "$TMPNAME"
}


tearDown() {
	rm "$TMPNAME"
}

. ./common_tests $0
