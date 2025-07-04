grml-live
=========

grml-live is a build system for creating a [Grml](https://grml.org/) and [Debian](https://www.debian.org/) based Linux Live system.

The build system is based on the class concept of FAI ([Fully Automatic Installation](https://fai-project.org/)).

Building a Debian based 64bit live system is as simple as running:

    # grml-live -s sid -a amd64 -c GRML_FULL

You can fully customize the build process, including adding
additional software and your very own configuration files.

Further information is available from https://grml.org/grml-live/

In case you want to run grml-live directly from the checkout
(after making sure all dependencies are installed), you should
set `GRML_FAI_CONFIG` and the `LIVE_CONF` variables so that it
does not use the config files of an installed `grml-live` package:

    # export GRML_FAI_CONFIG=$(pwd)/config
    # export LIVE_CONF=$(pwd)/etc/grml/grml-live.conf
    # ln -s ../../../grml-live-grml/templates/boot/addons templates/boot/  # optional
    # ./grml-live -s sid -a amd64 -c GRML_FULL
