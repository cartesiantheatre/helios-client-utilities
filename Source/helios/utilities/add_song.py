#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2019 Cartesian Theatre. All rights reserved.
#

# System imports...
import helios
from helios.utilities.common import add_common_arguments, zeroconf_find_server
from pprint import pprint
from termcolor import colored
import argparse
import attr
import base64
import colorama
import datetime
import sys
from tqdm import tqdm

import time

# i18n...
import gettext
_ = gettext.gettext

# Add arguments specific to this utility to argument parser...
def add_arguments(argument_parser):

    # Add a mutually exclusive group for song storage policy...
    storage_policy_group = argument_parser.add_mutually_exclusive_group()

    # Define behaviour for --no-store, defaults store to true...
    storage_policy_group.add_argument(
        '--no-store',
        action='store_false',
        default=True,
        dest='store',
        help=_('Delete the song on the server immediately after analysis. Defaults to store.'))

    # Define behaviour for --store, defaults store to true...
    storage_policy_group.add_argument(
        '--store',
        action='store_true',
        default=True,
        dest='store',
        help=_('Store the song after analysis on the server. Defaults to store.'))

    # Define behaviour for --reference...
    argument_parser.add_argument(
        '--reference',
        dest='song_reference',
        required=True,
        nargs='?',
        help=_('A free form alpha-numeric or underscore containing string to uniquely identify the new song within your catalogue.'))

    # Add input file to argument parser...
    argument_parser.add_argument(
        'song_file',
        help=_('Local path to song file to upload.'))

# Main function...
def main():

    # Initialize the argument parser...
    argument_parser = argparse.ArgumentParser(
        description=_('Add a song to a Helios server.'))

    # Add common arguments to argument parser...
    add_common_arguments(argument_parser)

    # Add arguments specific to this utility to argument parser...
    add_arguments(argument_parser)

    # Parse the command line...
    arguments = argument_parser.parse_args()

    # Initialize terminal colour...
    colorama.init()

    # Success flag to determine exit code...
    success = False

    # Try to submit the song...
    try:

        # If no host provided, use Zeroconf auto detection...
        if not arguments.host:
            arguments.host = zeroconf_find_server()[0]

        # Create a client...
        client = helios.client(
            token=arguments.token,
            host=arguments.host,
            port=arguments.port,
            verbose=arguments.verbose)

        # Prepare new song data...
        new_song_dict = {
            'file': base64.b64encode(open(arguments.song_file, 'rb').read()).decode('ascii'),
            'reference': arguments.song_reference
        }

        # Progress bar to be allocated by tqdm as soon as we know the total size...
        progress_bar = None

        # Progress bar callback...
        def progress_callback(bytes_read, new_bytes, bytes_total):

            # Reference the outer function...
            nonlocal progress_bar

            # If the progress bar hasn't been allocated already, do so now...
            if not progress_bar:
                progress_bar = tqdm(
                    desc=_('Uploading'),
                    leave=False,
                    smoothing=1.0,
                    total=bytes_total,
                    unit_scale=True,
                    unit='B')

            # Update the progress bar with the bytes just read...
            progress_bar.update(new_bytes)

#            time.sleep(0.001)

            # If we're done uploading, update description to analysis stage...
            if bytes_read == bytes_total:
                #progress_bar.n = 0
                progress_bar.set_description(_('Analyzing'))

            # Redraw the progress bar on the terminal...
            progress_bar.refresh()

        # Submit the song...
        stored_song = client.add_song(
            new_song_dict=new_song_dict,
            store=arguments.store,
            progress_callback=progress_callback)

        # Note the success...
        success = True

    # User trying to abort...
    except KeyboardInterrupt:
        sys.exit(1)

    # Helios exception...
    except helios.exceptions.ExceptionBase as someException:
        print(someException.what())

    # Some other kind of exception...
    except Exception as someException:
        print(_(f"An unknown exception occurred: {print(someException)}"))

    # Cleanup...
    finally:
        if progress_bar:
            progress_bar.close()

    # Show stored song model produced by server if successful and verbosity enabled...
    if success and arguments.verbose:
        pprint(attr.asdict(stored_song))

    # Show success status or failure...
    if success:
        print(_(f"[{colored(_(' OK '), 'green')}]: {arguments.song_file}"))
    else:
        print(_(f"[{colored(_('FAIL'), 'red')}]: {arguments.song_file}"))

    # If unsuccessful, bail...
    if not success:
        sys.exit(1)

    # Done...
    sys.exit(0)

# Entry point...
if __name__ == '__main__':
    main()

