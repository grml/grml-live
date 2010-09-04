#!/bin/bash
# Filename:      scripts/release_helper.sh
# Purpose:       helper script to build grml-live Debian packages (WFM style though)
# Authors:       grml-team (grml.org), (c) Michael Prokop <mika@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2 or any later version.
################################################################################

set -e
set -u

debian_version=''
script_version=''

if git status --porcelain | grep -q '^?? '; then
  printf "Uncommited changes in current working tree. Please commit/clean up.\n"
  exit 1
fi

printf "Building debian/changelog: "
git-dch --debian-branch="$(git branch | awk -F\*\  '/^* / { print $2}' )" \
        --since=v$(dpkg-parsechangelog | awk '/^Version:/ {print $2}') \
        --id-length=7 --meta --multimaint-merge -S
printf "OK\n"

$EDITOR debian/changelog

debian_version="$(dpkg-parsechangelog | awk '/^Version:/ {print $2}')"

dorelease="true"
if echo "$debian_version" | grep -q '\.gbp' ; then
  printf "Building snapshot version, not releasing.\n"
  dorelease="false"
fi

printf "Updating GRML_LIVE_VERSION string in grml-live script: "
sed -i "s/^GRML_LIVE_VERSION=.*/GRML_LIVE_VERSION='$debian_version'/" grml-live
printf "OK\n"

printf "Comparing versions of debian/changelog with grml-live version string: "
script_version="$(awk -F= '/^GRML_LIVE_VERSION=/ {print $2}' grml-live | sed "s/'//g")"
debian_version="$(dpkg-parsechangelog | awk '/^Version:/ {print $2}')"

if [[ "$script_version" == "$debian_version" ]] ; then
  printf "OK\n"
else
  printf "FAILED\n."
  printf "Debian package version ($debian_version) does not match script version ($script_version).\n"
  exit 1
fi

if $dorelease ; then
  git add debian/changelog grml-live
  git commit -s -m "Release new version ${debian_version}."
fi

printf "Building debian packages:\n"
git-buildpackage --git-debian-branch="$(git branch | awk -F\*\  '/^* / { print $2}' )" --git-ignore-new
printf "Finished execution of $(basename $0). Do not forget to tag release ${debian_version}\n"

## END OF FILE #################################################################
