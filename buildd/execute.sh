# Filename:      /usr/share/grml-live/buildd/execute.sh
# Purpose:       main execution file for grml-live buildd
# Authors:       grml-team (grml.org), (c) Michael Prokop <mika@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2 or any later version.
################################################################################

. /usr/share/grml-live/buildd/functions.sh || exit 1

# execute main grml-live
grml_live_run

# store logs on remote server
upload_logs

# store information about ISO size
iso_details

# create logs for adding to mail, but only if it fails
create_logs
send_mail -e

# move the ISO to final destination
store_iso

# clean exit
bailout

## END OF FILE #################################################################
