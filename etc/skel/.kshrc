# Filename:      .kshrc
# Purpose:       configuration file for the korn shell
# Authors:       grml-team (grml.org), (c) Michael Prokop <mika@grml.org>
# Bug-Reports:   see http://grml.org/bugs/
# License:       This file is licensed under the GPL v2.
# Latest change: Sam Mai 27 23:37:56 CEST 2006 [mika]
################################################################################

# ksh93 requires an editor
  set -o emacs

	# The $() has to be done to work around a bug in ksh that
	# isn't able to substitute with // inside the $HOME variable to have ~/
	# The control-character in the prompt is sadly neccessary for
	# color to be not disturbing for the command line editor.
[[ $USER != root ]] && PS1='[1;34m'"\
\$USER[0m@\$HOSTNAME \$(echo \$PWD | sed s,/home/\$USER,~,) $ "

[[ $USER  = root ]] && PS1='[1;31m'"\$USER[0m@\$HOSTNAME \$(
	if [[ $PWD = /root/* ]] ; then
		echo \$PWD|sed s,/root/,~/,
	elif [[ $PWD = /root ]] ; then
		echo \$PWD|sed s,/root,\~,
	fi
)# "

  export PS1
  alias ls='ls --color -F -trA'
  ff() { cd $1 && ls ; }
  alias md='mkdir -p'

## END OF FILE #################################################################
