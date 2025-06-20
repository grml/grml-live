#!/bin/bash
# Filename:      run_tests
# Purpose:       run unit tests for grml-autoconfig
# Authors:       grml-team (grml.org), (c) Ulrich Dangel <mru@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2.
################################################################################


GLOBRETVAL=0

if [ ! -f ./shunit2 ]; then
  # Use shunit2 directly from github, as all released versions are broken.
  curl -fsL -O https://raw.githubusercontent.com/kward/shunit2/refs/heads/master/shunit2
  chmod a+rx shunit2
fi

for FILE in test_*.sh ; do
  if [ -x "${FILE}" ] ; then
     pretty_name="${FILE##test_}"
     pretty_name="${pretty_name/.sh/}"

     echo "Running test for: ${pretty_name}"

     "./${FILE}"
     RETVAL=$?

     [ "$RETVAL" -ne 0 ] && GLOBRETVAL=$RETVAL
  fi
done

exit $GLOBRETVAL

## END OF FILE #################################################################
# vim:foldmethod=marker expandtab ai ft=zsh shiftwidth=2
