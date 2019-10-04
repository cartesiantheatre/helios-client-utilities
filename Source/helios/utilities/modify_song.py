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

    # Delete remote file...
    argument_parser.add_argument(
        '--delete-file',
        action='store_const',
        const='',
        dest='song_edit_file',
        help=_('Delete remote file if it was stored on server, but keep the database records.'))

    # Song album to replace existing field...
    argument_parser.add_argument(
        '--edit-album',
        dest='song_edit_album',
        required=False,
        nargs='?',
        help=_('Album to replace existing field.'))

    # Song artist to replace existing field...
    argument_parser.add_argument(
        '--edit-artist',
        dest='song_edit_artist',
        required=False,
        nargs='?',
        help=_('Artist to replace existing field.'))

    # Song file to replace existing field...
    argument_parser.add_argument(
        '--edit-file',
        dest='song_edit_file',
        required=False,
        nargs='?',
        help=_('Path to file to replace song with. Empty string means delete whatever was stored on the server.'))

    # Song genre to replace existing field...
    argument_parser.add_argument(
        '--edit-genre',
        dest='song_edit_genre',
        required=False,
        nargs='?',
        help=_('Genre to replace existing field.'))

    # Song isrc to replace existing field...
    argument_parser.add_argument(
        '--edit-isrc',
        dest='song_edit_isrc',
        required=False,
        nargs='?',
        help=_('ISRC to replace existing field.'))

    # Song reference to replace existing field...
    argument_parser.add_argument(
        '--edit-reference',
        dest='song_edit_reference',
        required=False,
        nargs='?',
        help=_('Reference to replace existing field.'))

    # Song title to replace existing field...
    argument_parser.add_argument(
        '--edit-title',
        dest='song_edit_title',
        required=False,
        nargs='?',
        help=_('Title to replace existing field.'))

    # Song year to replace existing field...
    argument_parser.add_argument(
        '--edit-year',
        dest='song_edit_year',
        required=False,
        nargs='?',
        help=_('Year to replace existing field.'),
        type=int)

# Main function...
def main():

    # Initialize the argument parser...
    argument_parser = argparse.ArgumentParser(
        description=_('Modify a song in a Helios server.'))

    # Add common arguments to argument parser...
    add_common_arguments(argument_parser)

    # Add arguments specific to this utility to argument parser...
    add_arguments(argument_parser)

    # Parse the command line...
    arguments = argument_parser.parse_args()

    # Initialize terminal colour...
    colorama.init()

    # Prepare to modify a song...
    patch_song_dict = {}

    # If --edit-file was explicitly passed an empty string, then instruct server
    #  to delete it's file, if it had one...
    if arguments.song_edit_file == '':
        patch_song_dict['file'] = ''

    # If a path was provided to --edit-file, load and submit the file...
    elif arguments.song_edit_file is not None:
        patch_song_dict['file'] = base64.b64encode(open(arguments.song_edit_file, 'rb').read()).decode('ascii')

    # Initialize all the other patchable song fields...
    if arguments.song_edit_album is not None: patch_song_dict['album'] = arguments.song_edit_album
    if arguments.song_edit_artist is not None: patch_song_dict['artist'] = arguments.song_edit_artist
    if arguments.song_edit_genre is not None: patch_song_dict['genre'] = arguments.song_edit_genre
    if arguments.song_edit_isrc is not None: patch_song_dict['isrc'] = arguments.song_edit_isrc
    if arguments.song_edit_reference is not None: patch_song_dict['reference'] = arguments.song_edit_reference
    if arguments.song_edit_title is not None: patch_song_dict['title'] = arguments.song_edit_title
    if arguments.song_edit_year is not None: patch_song_dict['year'] = arguments.song_edit_year

    # Try to modify the song...
    success = False
    try:

        # If no host provided, use Zeroconf auto detection...
        if not arguments.host:
            arguments.host = zeroconf_find_server()[0]

        # Create a client...
        client = helios.client(
            key=arguments.key,
            host=arguments.host,
            port=arguments.port,
            verbose=arguments.verbose)

        # Submit modification request...
        stored_song = client.modify_song(
            patch_song_dict=patch_song_dict,
            store=arguments.store,
            song_id=arguments.song_id,
            song_reference=arguments.song_reference)

        # Note success...
        success = True

    # Helios exception...
    except helios.exceptions.ExceptionBase as someException:
        print(someException.what())

    # Some other kind of exception...
    except Exception as someException:
        print(_(f"An unknown exception occurred: {print(someException)}"))

    # Show stored song model produced by server if successful...
    if success:
        pprint(attr.asdict(stored_song))

    # If unsuccessful, bail...
    if not success:
        sys.exit(1)

    # Done...
    sys.exit(0)

# Entry point...
if __name__ == '__main__':
    main()

