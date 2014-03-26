grml-live
=========

grml-live is a build system for creating a
[Grml](http://grml.org/) and [Debian](http://www.debian.org/)
based Linux Live system. The build system is based on FAI ([Fully
Automatic Installation](http://fai-project.org/)).

Building a Debian based 64bit live system is as simple as running:

    # grml-live -s sid -a amd64 -c GRMLBASE,GRML_FULL,AMD64

You can fully customize the build process, including adding
additional software and your very own configuration files.

Further information is available from http://grml.org/grml-live/

In case you want to run grml-live directly from the checkout (after
making sure all dependencies are installed), you should set
`GRML_FAI_CONFIG` so that it does not use the config files of an
installed `grml-live` package:

    # export GRML_FAI_CONFIG=$(pwd)/etc/grml/fai
    # ./grml-live -s sid -a amd64 -c GRMLBASE,GRML_FULL,AMD64
