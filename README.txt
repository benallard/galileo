Galileo
=======

:author: Benoît Allard <benoit.allard@gmx.de>
:version: 0.4dev
:license: LGPL
:bug tracker: https://bitbucket.org/benallard/galileo/issues
:mailing list: galileo@freelists.org (subscribe_, archive_)

.. _subscribe: mailto:galileo-request@freelists.org?subject=subscribe
.. _archive: http://freelists.org/archive/galileo/

Introduction
------------

This is a Python utility to securely synchronize a Fitbit device with the
Fitbit web service. It allows you to browse your data on their website, and
their apps.

All Bluetooth-based trackers are supported. Those are:

- Fitbit One
- Fitbit Zip
- Fitbit Flex
- Fitbit Force

.. note:: The Fitbit Ultra tracker is **not supported** as it communicates
          using the ANT protocol. To synchronize it, please use libfitbit_.

This utility is mainly targeted at Linux because Fitbit does not
provide any Linux-compatible software, but as Python is
cross-platform and the libraries used are available on a broad variety
of platforms, it should not be too difficult to port it to other
platforms.

.. _libfitbit: https://github.com/openyou/libfitbit

Main features
-------------

- Synchronize your fitbit tracker with the fitbit server using the provided
  dongle.
- Always communicate securely (using HTTPS) with the fitbit server.
- Saved all your dumps locally for possible later analyse.

Installation
------------

The easy way
~~~~~~~~~~~~

.. warning:: If you want to run the utility as a non-root user, you will have
             to install the udev rules manually (See `The more complicated
             way`_ or follow the instructions given when it fails).

::

    $ pip install galileo
    $ galileo

.. note:: If you don't want to install this utility system-wide, you
          may want to install it inside a virtualenv_, the behaviour
          will not be affected.

.. _virtualenv: http://www.virtualenv.org

The more complicated way
~~~~~~~~~~~~~~~~~~~~~~~~

First, you need to clone this repository locally, and install the required
dependencies:

- pyusb (need at least a 1.0 version, 0.4 and earlier are not compatible)
- requests.

You should copy the file ``99-fitbit.rules`` to the directory
``/etc/udev/rules.d`` in order to be able to run the utility as a
non-root user.

Don't forget to:

- restart the udev service: ``sudo service udev restart``
- unplug and re-insert the dongle to activate the new rule.

Then simply run the ``run`` script located at the root of this repository.

Documentation
-------------

For the moment, this README (and the ``--help`` command line option) is the
only documentation we have. The wiki_ is meant to gather technical
information about the project like the communication protocol, or the format
of the dump. Once this information reached a suffficient level of maturation,
the goal is to integrate it into the project documentation. So head-on there,
and start sharing your findings !

.. _wiki: https://bitbucket.org/benallard/galileo/wiki

Acknowledgements
----------------

Special thanks to the folks present @ the `issue 46`_ of libfitbit.

Especialy to `sansneural <https://github.com/sansneural>`_ for
https://docs.google.com/file/d/0BwJmJQV9_KRcSE0ySGxkbG1PbVE/edit and
`Ingo Lütkebohle`_ for http://pastebin.com/KZS2inpq.

.. _`issue 46`: https://github.com/openyou/libfitbit/issues/46
.. _`Ingo Lütkebohle`: https://github.com/iluetkeb
