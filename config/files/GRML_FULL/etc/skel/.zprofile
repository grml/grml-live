# handle automatic X.org/grml-x startup on Grml live system
if [ -r /etc/grml_cd ] ; then
  # /var/run/grml-x/window-manager is an ugly hack to share
  # selection of window manager via startx boot option
  # and grml-quickconfig with this startup wrapper
  if [ -r /var/run/grml-x/window-manager ] ; then
    [[ -z "$DISPLAY" && -n "$XDG_VTNR" && "$XDG_VTNR" -eq 7 ]] && grml-x "$(cat /var/run/grml-x/window-manager)"
  else
    [[ -z "$DISPLAY" && -n "$XDG_VTNR" && "$XDG_VTNR" -eq 7 ]] && grml-x
  fi
fi
