#!/usr/bin/env sh
# choose grml or more classic fluxbox keys file
[ "$1" = "grml" ] && sed -i '/session.keyFile/I  s/\/fluxkeys/\/keys/' ~/.fluxbox/init
[ "$1" = "fluxbox" ] && sed -i '/session.keyFile/I  s/\/keys/\/fluxkeys/ ' ~/.fluxbox/init
# toggle between config files
[ $# -eq 0 ] && sed -i '/session.keyFile/I  s/\/keys/\/fluxkeys/ ; t ; s/\/fluxkeys/\/keys/ ; t' ~/.fluxbox/init
# reload configuration
pkill -SIGUSR2 fluxbox
