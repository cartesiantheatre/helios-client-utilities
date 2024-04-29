#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2024 Cartesian Theatre. All rights reserved.
#

# System imports...
import argparse
import os
import sys

# Other imports...
import helios
from helios_client_utilities.common import add_common_arguments, zeroconf_find_server

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


# Main function...
def main():

    # Initialize the argument parser...
    argument_parser = argparse.ArgumentParser(
        description=_('Download a song from a remote Helios server.'))

    # Add common arguments to argument parser...
    add_common_arguments(argument_parser)

    # Add arguments specific to this utility to argument parser...
    add_arguments(argument_parser)

    # Parse the command line...
    arguments = argument_parser.parse_args()

    # Flag to signal download was successful...
    success = False

    # Try to download requested song...
    try:

        # If no host provided, use Zeroconf auto detection...
        if not arguments.host:

            # Get the list of all IP addresses for every interface for the best
            #  server, its port, and TLS flag...
            addresses, arguments.port, arguments.tls = zeroconf_find_server()

            # Select the first interface on the server...
            arguments.host = addresses[0]

        # Create a client...
        client = helios.Client(
            host=arguments.host,
            port=arguments.port,
            api_key=arguments.api_key,
            timeout_connect=arguments.timeout_connect,
            timeout_read=arguments.timeout_read,
            tls=arguments.tls,
            tls_ca_file=arguments.tls_ca_file,
            tls_certificate=arguments.tls_certificate,
            tls_key=arguments.tls_key,
            verbose=arguments.verbose)

        # Download...
        client.get_song_download(
            song_id=arguments.song_id,
            song_reference=arguments.song_reference,
            output=arguments.output,
            tui_progress=True)

        # Note success...
        success = True

    # User trying to abort. Remove partial download...
    except KeyboardInterrupt:
        os.remove(arguments.output)
        sys.exit(1)

    # Helios exception...
    except helios.exceptions.ExceptionBase as some_exception:
        print(some_exception.what())

    # Some other kind of exception...
    except Exception as some_exception:
        print(_(f"An unknown exception occurred: {print(some_exception)}"))

    # If unsuccessful, bail...
    if not success:
        sys.exit(1)

    # Done...
    sys.exit(0)

# Entry point...
if __name__ == '__main__':
    main()

