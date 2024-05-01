#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2024 Cartesian Theatre. All rights reserved.
#

# Import modules...
from __future__ import with_statement
from setuptools import setup, find_packages
import importlib.util
import os
import sys

# To allow this script to be run from any path, change the current directory to
#  the one hosting this script so that setuptools can find the required files...
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

# Get the long description from the README.md...
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
    spec = importlib.util.spec_from_file_location('version', 'Source/helios_client_utilities/__version__.py')
    spec.cached = None # Doesn't work
    version_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(version_module)

    # Return the version string...
    return version_module.version

# Provide setup parameters for package...
setup(

    # Metadata...
    author='Cartesian Theatre',
    author_email='kip@heliosmusic.io',
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
    keywords=[
        'music',
        'similarity',
        'match',
        'catalogue',
        'digital',
        'signal',
        'processing',
        'machine',
        'learning'],
    license='GPL',
    long_description=get_long_description(),
    long_description_content_type='text/markdown',
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
        'PyGObject >= 3.22',
        'helios-client',
        'importlib_resources',
        'keyring',
        'mutagen >= 1.3',
        'python-magic',
        'netifaces',
        'numpy',
        'pandas >= 0.23.3',
        'pillow',
        'requests',
        'requests-toolbelt',
        'simplejson',
        'termcolor',
        'tqdm',
        'urllib3',
        'zeroconf >= 0.27.0'
    ],
    package_dir={'': 'Source'},
    packages=find_packages(where='Source'),
    data_files=[
        ('share/applications', ['Data/share/applications/com.cartesiantheatre.helios_trainer.desktop']),
        ('share/applications/helios-trainer/text', ['Data/share/applications/helios-trainer/text/quick_start_page.txt']),
        ('share/applications/helios-trainer', ['Data/share/applications/helios-trainer/login_logo.png']),
        ('share/bash-completion/completions', ['Data/share/bash-completion/completions/helios-add-song']),
        ('share/bash-completion/completions', ['Data/share/bash-completion/completions/helios-delete-song']),
        ('share/bash-completion/completions', ['Data/share/bash-completion/completions/helios-download-song']),
        ('share/bash-completion/completions', ['Data/share/bash-completion/completions/helios-get-song']),
        ('share/bash-completion/completions', ['Data/share/bash-completion/completions/helios-import-songs']),
        ('share/bash-completion/completions', ['Data/share/bash-completion/completions/helios-learn']),
        ('share/bash-completion/completions', ['Data/share/bash-completion/completions/helios-modify-song']),
        ('share/bash-completion/completions', ['Data/share/bash-completion/completions/helios-provision-magnatune']),
        ('share/bash-completion/completions', ['Data/share/bash-completion/completions/helios-similar']),
        ('share/bash-completion/completions', ['Data/share/bash-completion/completions/helios-status']),
        ('share/bash-completion/completions', ['Data/share/bash-completion/completions/helios-trainer']),
        ('share/icons/hicolor/16x16/apps', ['Data/share/icons/hicolor/16x16/apps/com.cartesiantheatre.helios_trainer.png']),
        ('share/icons/hicolor/24x24/apps', ['Data/share/icons/hicolor/24x24/apps/com.cartesiantheatre.helios_trainer.png']),
        ('share/icons/hicolor/32x32/apps', ['Data/share/icons/hicolor/32x32/apps/com.cartesiantheatre.helios_trainer.png']),
        ('share/icons/hicolor/48x48/apps', ['Data/share/icons/hicolor/48x48/apps/com.cartesiantheatre.helios_trainer.png']),
        ('share/icons/hicolor/64x64/apps', ['Data/share/icons/hicolor/64x64/apps/com.cartesiantheatre.helios_trainer.png']),
        ('share/icons/hicolor/128x128/apps', ['Data/share/icons/hicolor/128x128/apps/com.cartesiantheatre.helios_trainer.png']),
        ('share/icons/hicolor/256x256/apps', ['Data/share/icons/hicolor/256x256/apps/com.cartesiantheatre.helios_trainer.png']),
        ('share/icons/hicolor/scalable/apps', ['Data/share/icons/hicolor/scalable/apps/com.cartesiantheatre.helios_trainer.svg']),
        ('share/icons/hicolor/scalable/mimetypes', ['Data/share/icons/hicolor/scalable/mimetypes/com.cartesiantheatre.helios_training_session.svg']),
        ('share/icons/hicolor/symbolic/apps', ['Data/share/icons/hicolor/symbolic/apps/com.cartesiantheatre.helios_trainer.svg']),
        ('share/mime/packages', ['Data/share/mime/packages/helios-trainer-mime.xml'])
    ],
    entry_points={
        'console_scripts': [
            'helios-add-song = helios_client_utilities.add_song:main',
            'helios-delete-song = helios_client_utilities.delete_song:main',
            'helios-download-song = helios_client_utilities.download_song:main',
            'helios-find-servers = helios_client_utilities.find_servers:main',
            'helios-get-song = helios_client_utilities.get_song:main',
            'helios-import-songs = helios_client_utilities.import_songs:main',
            'helios-learn = helios_client_utilities.learn:main',
            'helios-modify-song = helios_client_utilities.modify_song:main',
            'helios-provision-magnatune = helios_client_utilities.provision_magnatune:main',
            'helios-similar = helios_client_utilities.similar:main',
            'helios-status = helios_client_utilities.status:main'
        ],
        'gui_scripts': [
            'helios-trainer = helios_client_utilities.trainer.main:main'
        ]
    },
    python_requires='>= 3.10',
    zip_safe=True
)

