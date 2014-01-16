#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    from setuptools import setup
except ImportError:
    import distribute_setup
    distribute_setup.use_setuptools()
    from setuptools import setup

with open('README.txt') as file:
    long_description = file.read()

setup(
    name="galileo",
    version='0.2',
    description="Utility to synchronize a Fitbit tracker with the Fitbit server",
    long_description=long_description,
    author="Benoît Allard",
    author_email="benoit.allard@gmx.de",
    url="https://bitbucket.org/benallard/galileo",
    platforms='any',
    keywords=['fitbit', 'synchronize', 'health', 'tracker'],
    license="LGPL",
    install_requires=["requests","pyusb"],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)',
        'Environment :: Console',
        'Topic :: Utilities',
        'Topic :: Internet',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    py_modules=['galileo'],
    entry_points={
        'console_scripts':[
            'galileo = galileo:main'
        ],
    },
)
