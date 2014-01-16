Galileo
=======

:author: Benoît Allard <benoit.allard@gmx.de>
:version: 0.2
:license: LGPL
:bug tracker: https://bitbucket.org/benallard/galileo/issues

Introduction
------------

This is a python script to synchronise a Fitbit device with the fitbit server.
It allows you to browse your data on their website, and their apps.

All bluetooth based trackers are supported. Those are :

- Fitbit One
- Fitbit Zip
- Fitbit Flex
- Fitbit Force (?)

.. note:: The Fitbit Ultra tracker is **not supported** as it communicates
          using the ANT protocol. To synchronize it, please use libfitbit_.

This is mainly targetted at Linux as fitbit does not provide software to
synchronize their device there. But as python is cross-platform and the used
libraries are available on a broad variety of platform also, it should not be
too difficult to port it to other platforms.

.. _libfitbit: https://github.com/openyou/libfitbit

Installation
------------

First, you need to clone this repository locally, (or download the
``galileo.py`` script to you local machine), and install the required
dependencies:

- pyusb (tested with 1.0.0b1)
- requests (tested with 2.0.1)

You should copy the file ``50-fitbit.rules`` in the directory
``/etc/udev/rules.d`` in order to be able to run the script as a normal user.

Don't forget to:

- replace my username (``ben``) with yours.
- restart the udev service: ``sudo service udev restart``
- unplug and replug the dongle to activate the new rule.

Then simply run the ``galileo.py`` script.

Example
-------

An example trace can be found in the file ``trace.txt``.

Acknowledgements
----------------

Special thanks to the folks present @ the `issue 46`_ of libfitbit.

Especialy to `sansneural <https://github.com/sansneural>`_ for
https://docs.google.com/file/d/0BwJmJQV9_KRcSE0ySGxkbG1PbVE/edit and
`Ingo Lütkebohle`_ for http://pastebin.com/KZS2inpq.

.. _`issue 46`: https://github.com/openyou/libfitbit/issues/46
.. _`Ingo Lütkebohle`: https://github.com/iluetkeb
