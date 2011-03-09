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

if [ -n "${AUTOBUILD:-}" ] ; then
  git checkout autobuild # has to exist
else
  if git status --porcelain | grep -q '^?? '; then
    printf "Uncommited changes in current working tree. Please commit/clean up.\n"
    exit 1
  fi
fi

if [ -n "${AUTOBUILD:-}" ] ; then
  since=$(git show -s --pretty="tformat:%h")
else
  since=v$(dpkg-parsechangelog | awk '/^Version:/ {print $2}')
fi

printf "Building debian/changelog: "
git-dch --ignore-branch --since=$since \
        --id-length=7 --meta --multimaint-merge -S
printf "OK\n"

if [ -z "${AUTOBUILD:-}" ] ; then
  if ! $EDITOR debian/changelog ; then
    printf "Exiting as editing debian/changelog returned an error." >&2
    exit 1
  fi
fi

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

if $dorelease || [ -n "${AUTOBUILD:-}" ] ; then
  git add debian/changelog grml-live
  git commit -s -m "Release new version ${debian_version}."
fi

printf "Building debian packages:\n"
if [ -n "${AUTOBUILD:-}" ] ; then
  [ -d ../grml-live.build-area ] || mkdir ../grml-live.build-area
  git-buildpackage --git-ignore-branch --git-ignore-new --git-export-dir=../grml-live.build-area -us -uc
else
  git-buildpackage --git-ignore-branch --git-ignore-new $*
  printf "Finished execution of $(basename $0). Do not forget to tag release ${debian_version}\n"
fi

if [ -n "${AUTOBUILD:-}" ] ; then
   (
     cd ../grml-live.build-area
     dpkg-scanpackages . /dev/null > Packages
   )
   apt-get update
   PACKAGES=$(dpkg --list grml-live\* | awk '/^ii/ {print $2}')
   apt-get -y --allow-unauthenticated install $PACKAGES
fi

## END OF FILE #################################################################
