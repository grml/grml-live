#!/bin/sh
pid=/var/run/brltty

[ ! -x /sbin/brltty ] && exit 0

[ -r $pid ] && kill -0 `cat $pid` && exit 0
exec /sbin/brltty -P $pid "$@"
