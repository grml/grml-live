# handle automatic X.org/grml-x startup on Grml live system
if [ -r /etc/grml_cd ] ; then
  [[ -z "$DISPLAY" && -n "$XDG_VTNR" && "$XDG_VTNR" -eq 7 ]] && grml-x
fi
