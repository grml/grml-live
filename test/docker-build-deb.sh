#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
#
# Build a deb.
# To be run inside docker, as this script assumes it can modify the running OS.

set -eu -o pipefail
set -x

if [ "${1:-}" != "--autobuild" ]; then
  echo "$0: Only intended for CI scenarios, will destroy source files and modify running OS." >&2
  exit 1
fi
BUILD_NUMBER="${2:-}"
if [ -z "$BUILD_NUMBER" ]; then
  echo "$0: missing build number in arguments" >&2
  exit 1
fi

apt-get update
apt-get install -qq -y --no-install-recommends build-essential devscripts equivs

SOURCEDIR=$PWD

cd /tmp
mk-build-deps -ir -t 'apt-get -o Debug::pkgProblemResolver=yes --no-install-recommends -y' "$SOURCEDIR"/debian/control

dpkg-source -b "$SOURCEDIR"
dpkg-source -x ./*.dsc builddir
cd builddir

OLD_VERSION=$(dpkg-parsechangelog -SVersion)

cat > debian/changelog <<EOT
grml-live (${OLD_VERSION}+autobuild${BUILD_NUMBER}) UNRELEASED; urgency=medium

  * Automated Build

 -- Automated Build <builder@localhost>  $(date -R)
EOT

dpkg-buildpackage -b --no-sign

mv ../*deb "$SOURCEDIR"/
