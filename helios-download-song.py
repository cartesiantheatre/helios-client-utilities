#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2019 Cartesian Theatre. All rights reserved.
#

# System imports...
import helios
from common import add_common_arguments, zeroconf_find_server
from hfilesize import Format, FileSize
from pprint import pprint
from termcolor import colored
import argparse
import attr
import colorama
import datetime
import sys

# i18n...
import gettext
_ = gettext.gettext

# Add arguments specific to this utility to argument parser...
def add_arguments(argument_parser):

    # Add a mutually exclusive group for song selection, either by ID or
    #  reference...
    song_selection_group = argument_parser.add_mutually_exclusive_group(required=True)

    # Define behaviour for --id in song selection exclusion group...
    song_selection_group.add_argument(
        '--id',
        dest='song_id',
        required=False,
        nargs='?',
        help=_('Unique numeric identifier of song to modify. You must provide either this or a --reference.'),
        type=int)

    # Define behaviour for --reference in song selection exclusion group...
    song_selection_group.add_argument(
        '--reference',
        dest='song_reference',
        required=False,
        nargs='?',
        help=_('Unique reference of song to modify. You must provide either this or an --id.'))

    # Define behaviour for --output...
    argument_parser.add_argument(
        '-o', '--output',
        action='store',
        default=None,
        dest='output',
        required=True,
        help=_('Write out song to disk with the given file name.'))


# Entry point...
if __name__ == '__main__':

    # Initialize the argument parser...
    argument_parser = argparse.ArgumentParser(
        description=_('Download a song from a remote Helios server.'))

    # Add common arguments to argument parser...
    add_common_arguments(argument_parser)

    # Add arguments specific to this utility to argument parser...
    add_arguments(argument_parser)

    # Parse the command line...
    arguments = argument_parser.parse_args()

    # Initialize terminal colour...
    colorama.init()

    # Flag to signal download was successful...
    success = False

    # Try to download requested song...
    try:

        # If no host provided, use Zeroconf auto detection...
        if not arguments.host:
            arguments.host = zeroconf_find_server()[0]

        # Create a client...
        client = helios.client(
            host=arguments.host,
            port=arguments.port,
            token=arguments.token,
            verbose=arguments.verbose)

        # Download...
        client.get_song_download(
            song_id=arguments.song_id,
            song_reference=arguments.song_reference,
            output=arguments.output,
            progress=True)

        # Note success...
        success = True

    # User trying to abort. Remove partial download...
    except KeyboardInterrupt:
        os.remove(output)
        sys.exit(1)

    # Helios exception...
    except helios.exceptions.ExceptionBase as someException:
        print(someException.what())

    # Some other kind of exception...
    except Exception as someException:
        print(_(f"An unknown exception occurred: {print(someException)}"))

    # If unsuccessful, bail...
    if not success:
        sys.exit(1)

    # Done...
    sys.exit(0)

