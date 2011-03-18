#!/bin/bash
# Filename:      scripts/release_helper.sh
# Purpose:       helper script to build grml-live Debian packages
# Authors:       grml-team (grml.org), (c) Michael Prokop <mika@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2 or any later version.
################################################################################

set -e
set -u

export LC_ALL=C
export LANG=C

debian_version=''
script_version=''

autobuild_branch="autobuild_$(date +%Y%m%d_%H%M%S)"

if [ -n "${AUTOBUILD:-}" ] ; then
  git checkout master
  git pull
  git checkout -b "$autobuild_branch"
else
  if git status --porcelain | grep -q '^?? '; then
    printf "Uncommited changes in current working tree. Please commit/clean up.\n"
    exit 1
  fi
fi

printf "Building debian/changelog: "
if [ -n "${AUTOBUILD:-}" ] ; then
  # since=$(git show -s --pretty="tformat:%h")
  eval $(grep '^GRML_LIVE_VERSION=' grml-live)
  DATE=$(date -R)
  UNIXTIME=$(date +%s)

  cat > debian/changelog << EOF
grml-live (${GRML_LIVE_VERSION}~autobuild${UNIXTIME}) UNRELEASED; urgency=low

  * Automatically built package based on the state of
    git repository at http://git.grml.org/?p=grml-live.git
    on $DATE ->

    $(git log --format=oneline -1)

 -- grml-live Auto Build <grml-live-git@$(hostname)>  $DATE

EOF
  git add debian/changelog
  git commit -m "Releasing ${GRML_LIVE_VERSION}-~autobuild${UNIXTIME} (auto build)"
else
  since=v$(dpkg-parsechangelog | awk '/^Version:/ {print $2}')
  git-dch --ignore-branch --since=$since \
          --id-length=7 --meta --multimaint-merge -S
  printf "OK\n"
fi

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
  rm -rf ../grml-live.build-area/grml-live* # otherwise we're keeping files forever...
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
   git checkout master
   git branch -D ${autobuild_branch} || true
   sudo apt-get update
   PACKAGES=$(dpkg --list grml-live\* | awk '/^ii/ {print $2}')
   sudo apt-get -y --allow-unauthenticated install $PACKAGES
fi

## END OF FILE #################################################################
