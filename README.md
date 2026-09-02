grml-live
=========

grml-live is a build system for creating a [Grml](https://grml.org/) and [Debian](https://www.debian.org/) based Linux Live system.

The build system is based on the class concept of FAI ([Fully Automatic Installation](https://fai-project.org/)).

Building a Debian based live system is as simple as running:

    $ grml-live -s sid -c GRML_FULL

You can fully customize the build process, including adding
additional software and your very own configuration files.

Further information is available from https://grml.org/grml-live/

You can run grml-live directly from the checkout. Just make sure
all dependencies are installed (best see `debian/control` for a list).

Example:

    $ ln -s ../../../grml-live-grml/templates/arch config/media-files/GRMLBASE/  # optional
    $ ./grml-live -s sid -c GRML_FULL ./my-grml-build
