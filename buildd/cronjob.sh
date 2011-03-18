#!/bin/sh
# Filename:      cronjob.sh
# Purpose:       example for a grml-live buildd cronjob setup
# Authors:       grml-team (grml.org), (c) Michael Prokop <mika@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2 or any later version.
################################################################################
# Add something like that to the crontab to execute grml-live buildd
# every day at a specific time:
# 50 0 * * * /usr/share/grml-live/buildd/cronjob.sh
#
# On the mirror (where you're hosting the ISOs) you might want to
# install something like that in your crontab:
# 02  * * * * /home/mika/cronjobs/link_latest.sh
# 03 03 * * * /home/mika/cronjobs/cleanup.sh
################################################################################

if [ -r /usr/share/grml-live/buildd/buildd_running ] ; then
  echo "already running instance of grml-live buildd found, exiting.">&2
  echo "if you think this is not true: rm /usr/share/grml-live/buildd/buildd_running">&2
  exit 1
fi

echo $$ > /usr/share/grml-live/buildd/buildd_running

/usr/share/grml-live/buildd/grml-live_autobuild_grml64-small_squeeze.sh && \
/usr/share/grml-live/buildd/grml-live_autobuild_grml64-small_wheezy.sh && \
/usr/share/grml-live/buildd/grml-live_autobuild_grml64-small_sid.sh && \
/usr/share/grml-live/buildd/grml-live_autobuild_grml-small_squeeze.sh && \
/usr/share/grml-live/buildd/grml-live_autobuild_grml-small_wheezy.sh && \
/usr/share/grml-live/buildd/grml-live_autobuild_grml-small_sid.sh

/usr/share/grml-live/buildd/upload_isos.sh && \
/usr/share/grml-live/buildd/remove_isos.sh

/usr/share/grml-live/buildd/grml-live_autobuild_grml64-medium_squeeze.sh && \
/usr/share/grml-live/buildd/grml-live_autobuild_grml64-medium_wheezy.sh && \
/usr/share/grml-live/buildd/grml-live_autobuild_grml64-medium_sid.sh && \
/usr/share/grml-live/buildd/grml-live_autobuild_grml-medium_squeeze.sh && \
/usr/share/grml-live/buildd/grml-live_autobuild_grml-medium_wheezy.sh && \
/usr/share/grml-live/buildd/grml-live_autobuild_grml-medium_sid.sh

/usr/share/grml-live/buildd/upload_isos.sh && \
/usr/share/grml-live/buildd/remove_isos.sh

/usr/share/grml-live/buildd/grml-live_autobuild_grml64-large_squeeze.sh && \
/usr/share/grml-live/buildd/grml-live_autobuild_grml64-large_wheezy.sh && \
/usr/share/grml-live/buildd/grml-live_autobuild_grml64-large_sid.sh && \
/usr/share/grml-live/buildd/grml-live_autobuild_grml-large_squeeze.sh && \
/usr/share/grml-live/buildd/grml-live_autobuild_grml-large_wheezy.sh && \
/usr/share/grml-live/buildd/grml-live_autobuild_grml-large_sid.sh

/usr/share/grml-live/buildd/upload_isos.sh && \
/usr/share/grml-live/buildd/remove_isos.sh

rm -f /usr/share/grml-live/buildd/buildd_running

## END OF FILE #################################################################
