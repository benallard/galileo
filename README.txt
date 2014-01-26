Galileo
=======

:author: Benoît Allard <benoit.allard@gmx.de>
:version: 0.2
:license: LGPL
:bug tracker: https://bitbucket.org/benallard/galileo/issues
:mailing list: galileo@freelists.org (subscribe_, archive_)

.. _subscribe: mailto:galileo-request@freelists.org?subject=subscribe
.. _archive: http://freelists.org/archive/galileo/

Introduction
------------

This is a Python utility to synchronize a Fitbit device with the Fitbit
web service. It allows you to browse your data on their website, and
their apps.

All Bluetooth-based trackers are supported. Those are:

- Fitbit One
- Fitbit Zip
- Fitbit Flex
- Fitbit Force

.. note:: The Fitbit Ultra tracker is **not supported** as it communicates
          using the ANT protocol. To synchronize it, please use libfitbit_.

This utility is mainly targeted at Linux because Fitbit does not
provide any Linux-compatible software but, as Python is
cross-platform and the libraries used are available on a broad variety
of platforms, it should not be too difficult to port it to other
platforms.

.. _libfitbit: https://github.com/openyou/libfitbit

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

.. _issue10: https://bitbucket.org/benallard/galileo/issue/10
.. _virtualenv: http://www.virtualenv.org

The more complicated way
~~~~~~~~~~~~~~~~~~~~~~~~

First, you need to clone this repository locally, (or download the
``galileo.py`` script to you local machine), and install the required
dependencies:

- pyusb (tested with 1.0.0b1)
- requests (tested with 2.0.1)

You should copy the file ``99-fitbit.rules`` to the directory
``/etc/udev/rules.d`` in order to be able to run the utility as a
non-root user.

Don't forget to:

- restart the udev service: ``sudo service udev restart``
- unplug and re-insert the dongle to activate the new rule.

Then simply run ``galileo.py``.

Example
-------

An example trace can be found in the file ``trace.txt``.

Run the utility with the ``--help`` argument to see a list of available options
to control the synchronization behavior.

Acknowledgements
----------------

Special thanks to the folks present @ the `issue 46`_ of libfitbit.

Especialy to `sansneural <https://github.com/sansneural>`_ for
https://docs.google.com/file/d/0BwJmJQV9_KRcSE0ySGxkbG1PbVE/edit and
`Ingo Lütkebohle`_ for http://pastebin.com/KZS2inpq.

.. _`issue 46`: https://github.com/openyou/libfitbit/issues/46
.. _`Ingo Lütkebohle`: https://github.com/iluetkeb
