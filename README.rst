Galileo
=======

:author: Benoît Allard <benoit.allard@gmx.de>
:version: 0.2
:license: LGPL
:bug tracker: https://bitbucket.org/benallard/galileo/issues

Introduction
------------

This is a python script to synchronise a fitbit device with the fitbit server.

Installation
------------

First, you need to clone this repository locally, (or download the script to you local machine), and install the required dependencies:

- pyusb (tested with 1.0.0b1)
- requests (tested with 2.0.1)

You should copy the file ``50-fitbit.rules`` in the directory ``/etc/udev/rules.d`` in order to be able to run the script as a normal user. (Don't forget to replace my username with yours, and to unplug and replug the dongle for the rule to be active).

Then simply run the script.

Example
-------

An example trace can be found in the file ``trace.txt``.

Thanks
------

Special thanks to the folks present @ the `issue 46`_ of libfitbit.

Especialy to `sansneural <https://github.com/sansneural>`_ for
https://docs.google.com/file/d/0BwJmJQV9_KRcSE0ySGxkbG1PbVE/edit and
`Ingo Lütkebohle`_ for http://pastebin.com/KZS2inpq.

.. _`issue 46`: https://github.com/openyou/libfitbit/issues/46
.. _`Ingo Lütkebohle`: https://github.com/iluetkeb
