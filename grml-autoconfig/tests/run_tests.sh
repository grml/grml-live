#!/bin/zsh
# Filename:      run_tests
# Purpose:       run unit tests for grml-autoconfig
# Authors:       grml-team (grml.org), (c) Ulrich Dangel <mru@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2.
################################################################################


GLOBRETVAL=0

for FILE in test_*.sh ; do
  if [ -x ${FILE} ] ; then
     pretty_name="${FILE##test_}"
     pretty_name="${pretty_name/.sh/}"

     echo "Running test for: ${pretty_name}"

     ./${FILE}
     RETVAL=$?

     [ "$RETVAL" -ne 0 ] && GLOBRETVAL=$RETVAL
  fi
done

exit $GLOBRETVAL

## END OF FILE #################################################################
# vim:foldmethod=marker expandtab ai ft=zsh shiftwidth=3
