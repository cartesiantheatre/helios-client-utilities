#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2021 Cartesian Theatre. All rights reserved.
#

# System imports...
import argparse
import base64
from pprint import pprint
import sys

# Other imports...
import helios
from helios.responses import StoredSongSchema
from helios.utilities.common import add_common_arguments, zeroconf_find_server

# i18n...
import gettext
_ = gettext.gettext

# Add arguments specific to this utility to argument parser...
def add_arguments(argument_parser):

    # Add a mutually exclusive group for song search key selection...
    search_key_selection_group = argument_parser.add_mutually_exclusive_group(required=True)

    # Define behaviour for --file in song search key selection exclusion group...
    search_key_selection_group.add_argument(
        '--file',
        dest='similar_file',
        required=False,
        help=_('Path  to a local song file to use as a search key on the server.'))

    # Define behaviour for --id in song search key selection exclusion group...
    search_key_selection_group.add_argument(
        '--id',
        dest='similar_id',
        required=False,
        nargs='?',
        help=_('Unique  numeric  identifier  of song already within the database to use as a search key.'),
        type=int)

    # Define behaviour for --reference in song search key selection exclusion group...
    search_key_selection_group.add_argument(
        '--reference',
        dest='similar_reference',
        required=False,
        nargs='?',
        help=_('Unique reference of song already within the database to use as a search key.'))

    # Define behaviour for --url in song search key selection exclusion group...
    search_key_selection_group.add_argument(
        '--url',
        dest='similar_url',
        required=False,
        nargs='?',
        help=_('URL  of  a  song  hosted  on  any of a number of supported external services to use as a search key on the server.'))

    # Define behaviour for --results...
    argument_parser.add_argument(
        '--results',
        dest='maximum_results',
        default=10,
        required=False,
        nargs='?',
        help=_('Maximum number of similarity results to return. Default is ten.'),
        type=int)

    # Define behaviour for --short...
    argument_parser.add_argument(
        '--short',
        action='store_true',
        default=False,
        dest='short',
        help=_('Display results in short form without any JSON as simply \"Artist - Title\" format.'))


# Main function...
def main():

    # Initialize the argument parser...
    argument_parser = argparse.ArgumentParser(
        description=_('Search for similar songs on a remote Helios server.'))

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

        # Prepare request parameters...
        similarity_search_dict = {}
        if arguments.similar_file:
            similarity_search_dict['similar_file'] = base64.b64encode(open(arguments.similar_file, 'rb').read()).decode('ascii')
        if arguments.similar_id:
            similarity_search_dict['similar_id'] = arguments.similar_id
        if arguments.similar_reference:
            similarity_search_dict['similar_reference'] = arguments.similar_reference
        if arguments.similar_url:
            similarity_search_dict['similar_url'] = arguments.similar_url
        similarity_search_dict['maximum_results'] = arguments.maximum_results

        # Query...
        similar_songs_list = client.get_similar_songs(similarity_search_dict)

        # Note success...
        success = True

        # Create a schema to deserialize stored song objects into JSON...
        stored_song_schema = StoredSongSchema()

        # Display each song and end with a new line...
        for song in similar_songs_list:

            # If we are not using short form output, display each song in JSON
            #  format...
            if not arguments.short:
                pprint(stored_song_schema.dump(song))
                print('')

            # Otherwise show it in short form...
            else:
                print(F'{song.artist} - {song.title}')

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
