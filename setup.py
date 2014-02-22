#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    from setuptools import setup, find_packages
except ImportError:
    import distribute_setup
    distribute_setup.use_setuptools()
    from setuptools import setup

with open('README.txt') as file:
    long_description = file.read()

setup(
    name="galileo",
    version='0.4dev',
    description="Utility to securely synchronize a Fitbit tracker with the"
                " Fitbit server",
    long_description=long_description,
    author="Benoît Allard",
    author_email="benoit.allard@gmx.de",
    url="https://bitbucket.org/benallard/galileo",
    platforms='any',
    keywords=['fitbit', 'synchronize', 'health', 'tracker'],
    license="LGPL",
    install_requires=[
        "requests",
        "pyusb>=1a"],  # version 1a doesn't exists, but is smaller than 1.0.0a2
    test_suite="tests",
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: GNU Lesser General Public License v3 or'
        ' later (LGPLv3+)',
        'Environment :: Console',
        'Topic :: Utilities',
        'Topic :: Internet',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'galileo = galileo.main:main'
        ],
    },
)
