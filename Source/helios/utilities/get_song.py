#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2021 Cartesian Theatre. All rights reserved.
#

# System imports...
import argparse
from pprint import pprint
import sys

# Other imports
import helios
from helios.responses import StoredSongSchema
from helios.utilities.common import add_common_arguments, zeroconf_find_server

# i18n...
import gettext
_ = gettext.gettext

# Add arguments specific to this utility to argument parser...
def add_arguments(argument_parser):

    # Add a mutually exclusive group for song selection, either by ID or
    #  reference...
    song_selection_group = argument_parser.add_mutually_exclusive_group(required=True)

    # Define behaviour for --all in song selection exclusion group...
    song_selection_group.add_argument(
        '--all',
        action='store_true',
        default=False,
        dest='all',
        help=_('Retrieve metadata for all songs.'))

    # Define behaviour for --id in song selection exclusion group...
    song_selection_group.add_argument(
        '--id',
        dest='song_id',
        required=False,
        nargs='?',
        help=_('Unique numeric identifier of song to query. You must provide '
               'exactly one of an --id, --reference, --all, or --random.'),
        type=int)

    # Define behaviour for --random in song selection exclusion group...
    song_selection_group.add_argument(
        '--random',
        dest='random_size',
        required=False,
        nargs='?',
        help=_('Randomly select <size> songs to retrieve from the catalogue. '
               'The <size> must be greater than or equal to 1 and no greater '
               'than the total number of songs in the catalogue. You must '
               'provide exactly one of --id, --reference, --all, or --random.'),
        type=int)

    # Define behaviour for --reference in song selection exclusion group...
    song_selection_group.add_argument(
        '--reference',
        dest='song_reference',
        required=False,
        nargs='?',
        help=_('Unique reference of song to query. You must provide exactly '
               'one of an --id, --reference, --all, or --random.'))

    # Define behaviour for --paginate...
    argument_parser.add_argument(
        '--paginate',
        dest='paginate',
        required=False,
        nargs='?',
        help=_('Number of results to buffer and show before pausing for user. '
               'By default there is no pause.'),
        type=int)

# Main function...
def main():

    # Initialize the argument parser...
    argument_parser = argparse.ArgumentParser(
        description=_('Query metadata for a song within a remote Helios server.'))

    # Add common arguments to argument parser...
    add_common_arguments(argument_parser)

    # Add arguments specific to this utility to argument parser...
    add_arguments(argument_parser)

    # Parse the command line...
    arguments = argument_parser.parse_args()

    # Status on whether there were any errors...
    success = False

    # Try to retrieve metadata...
    try:

        # If no host provided, use Zeroconf auto detection...
        if not arguments.host:
            arguments.host, arguments.port, arguments.tls = zeroconf_find_server()

        # Create a client...
        client = helios.client(
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

        # Create a schema to serialize stored song objects into JSON...
        stored_song_schema = StoredSongSchema()

        # For a specified single song...
        if arguments.song_id is not None or arguments.song_reference is not None:

            # Query...
            stored_song = client.get_song(
                song_id=arguments.song_id,
                song_reference=arguments.song_reference)

            # Note success...
            success = True

            # Show stored song model...
            pprint(stored_song_schema.dump(stored_song))

        # For a randomly selected song or songs...
        elif arguments.random_size is not None:

            # Query...
            random_stored_songs = client.get_random_songs(size=arguments.random_size)

            # Note success...
            success = True

            # Dump each song and end with a new line...
            for random_song in random_stored_songs:
                pprint(stored_song_schema.dump(random_song))
                print('')

        # For all songs...
        else:

            # Current results page index...
            current_page = 1

            # Number of results to retrieve per query if overridden by user,
            #  otherwise use default...
            if arguments.paginate:
                page_size = arguments.paginate
            else:
                page_size = 100

            # Keep fetching songs while there are some...
            while True:

                # Try to get a batch of songs for current page...
                page_songs_list = client.get_all_songs(
                    page=current_page, page_size=page_size)

                # None left...
                if len(page_songs_list) == 0:
                    break

                # Dump each song and end with a new line...
                for song in page_songs_list:
                    pprint(stored_song_schema.dump(song))
                    print('')

                # Seek to the next page...
                current_page += 1

                # If user asked that we pause after each batch, then wait for
                #  user...
                if arguments.paginate:
                    arguments.paginate = (input(_('Press enter to continue, or C to continue without pagination...')) != 'C')
                    print('')

            # Done...
            success = True

    # User trying to abort...
    except KeyboardInterrupt:
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
