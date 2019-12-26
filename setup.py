#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2019 Cartesian Theatre. All rights reserved.
#

# Import modules...
from __future__ import with_statement
from setuptools import setup, find_namespace_packages
import importlib.util
import os
import sys

# To allow this script to be run from any path, change the current directory to
#  the one hosting this script so that setuptools can find the required files...
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

# Get the long description from the ReadMe.md...
def get_long_description():
    long_description = []
    with open('README.md') as file:
        long_description.append(file.read())
    return '\n\n'.join(long_description)

# Read the module version directly out of the source...
def get_version():

    # Path to file containing version string...
    version_file = None

    # Load the version module...
    spec = importlib.util.spec_from_file_location('version', 'Source/helios/utilities/__version__.py')
    spec.cached = None # Doesn't work
    version_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(version_module)

    # Return the version string...
    return version_module.version

# Provide setup parameters for package...
setup(

    # Metadata...
    author='Cartesian Theatre',
    author_email='info@heliosmusic.io',
    classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Database :: Database Engines/Servers',
        'Topic :: Internet',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Indexing/Search',
        'Topic :: Multimedia :: Sound/Audio',
        'Topic :: Multimedia :: Sound/Audio :: Analysis',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'Topic :: Scientific/Engineering :: Physics',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Utilities'
    ],
    description='Utilities for interacting with a Helios server.',
    keywords=['music', 'similarity', 'match', 'catalogue', 'digital', 'signal', 'processing'],
    license='GPL',
    long_description=get_long_description(),
    name='helios-client-utilities',
    project_urls={
        'Bug Tracker': 'https://github.com/cartesiantheatre/helios-client-utilities/issues',
        'Documentation': 'https://heliosmusic.io/',
        'Source Code': 'https://github.com/cartesiantheatre/helios-client-utilities'
    },
    url='https://www.heliosmusic.io',
    version=get_version(),

    # Options...
    include_package_data=True,
    install_requires=[
        'attrs >= 18.2.0',
        'colorama',
        'helios-client',
        'pandas >= 0.23.3',
        'simplejson',
        'termcolor',
        'tqdm',
        'zeroconf'
    ],
    package_dir={'': 'Source'},
    packages=find_namespace_packages(where='Source'),
    entry_points={
        'console_scripts': [
            'helios-add-song = helios.utilities.add_song:main',
            'helios-delete-song = helios.utilities.delete_song:main',
            'helios-download-song = helios.utilities.download_song:main',
            'helios-find-servers = helios.utilities.find_servers:main',
            'helios-get-song = helios.utilities.get_song:main',
            'helios-import-songs = helios.utilities.import_songs:main',
            'helios-modify-song = helios.utilities.modify_song:main',
            'helios-similar = helios.utilities.similar:main',
            'helios-status = helios.utilities.status:main'
        ],
    },
    python_requires='>= 3.7',
    zip_safe=True
)

