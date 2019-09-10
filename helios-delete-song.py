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
from tqdm import tqdm

# i18n...
import gettext
_ = gettext.gettext

# Add arguments specific to this utility to argument parser...
def add_arguments(argument_parser):

    # Add a mutually exclusive group for song selection, either by ID or
    #  reference...
    song_selection_group = argument_parser.add_mutually_exclusive_group(required=True)

    # Define behaviour for --reference in song selection exclusion group...
    song_selection_group.add_argument(
        '--delete-all',
        action='store_true',
        default=False,
        dest='delete_all',
        help=_('Delete on the remote server all song metadata and song files.'))

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

    # Define behaviour for --delete-file-only in song selection exclusion group...
    argument_parser.add_argument(
        '--delete-file-only',
        action='store_true',
        default=False,
        dest='delete_file_only',
        help=_('Delete on the remote server the stored song file, but keep preserve the metadata of the analyzed.'))

# Delete a song by ID or reference. If delete_file_only is True, then only the
#  song file is deleted off the server, if it had one, but the metadata is
#  preserved. Returns true if a song file was deleted if delete_file_only
#  is true. If delete_file_only is False, always returns True on success or
#  throws an exception otherwise...
def delete_song(client, song_id, song_reference, delete_file_only=False):

    # Delete just the remote file itself...
    if delete_file_only:

        # See if the song already had a stored song...
        stored_song = client.get_song(
            song_id=song_id,
            song_reference=song_reference)

        # Prepare to instruct server to delete it's file, if it had one...
        patch_song_dict = { 'file' : '' }

        # Delete...
        modified_stored_song = client.modify_song(
            patch_song_dict=patch_song_dict,
            song_id=song_id,
            song_reference=song_reference)

        # Inform caller whether a file was deleted or not...
        return (stored_song.location and not modified_stored_song.location)

    # Delete it entirely...
    else:

        # Send request...
        client.delete_song(
            song_id=song_id,
            song_reference=song_reference)

        # Update statistics...
        return True


# Main function...
def main():

    # Initialize the argument parser...
    argument_parser = argparse.ArgumentParser(
        description=_('Delete a remote song or songs on a Helios server.'))

    # Add common arguments to argument parser...
    add_common_arguments(argument_parser)

    # Add arguments specific to this utility to argument parser...
    add_arguments(argument_parser)

    # Parse the command line...
    arguments = argument_parser.parse_args()

    # Initialize terminal colour...
    colorama.init()

    # Status on whether there were any errors...
    success = False

    # Try to delete a single song or all songs...
    try:

        # A progress bar we may or may not construct later...
        progress_bar = None

        # If no host provided, use Zeroconf auto detection...
        if not arguments.host:
            arguments.host = zeroconf_find_server()[0]

        # Create a client...
        client = helios.client(
            host=arguments.host,
            port=arguments.port,
            token=arguments.token,
            verbose=arguments.verbose)

        # Counter of the number of songs deleted...
        total_deleted = 0

        # Only requested a single song to delete...
        if arguments.song_id or arguments.song_reference:

            # Submit request to server...
            song_deleted = delete_song(
                client,
                song_id=arguments.song_id,
                song_reference=arguments.song_reference,
                delete_file_only=arguments.delete_file_only)

            # Update deletion counter...
            if song_deleted:
                total_deleted += 1

            # Note success...
            success = True

        # User requested to delete all song files only, keeping metadata...
        elif arguments.delete_all and arguments.delete_file_only:

            # Prompt user to make sure they are certain they know what they are
            #  doing...
            verification = input(_('Are you sure you know what you are doing? Type \'YES\': '))
            if verification != _('YES'):
                sys.exit(1)

            # How many songs are currently in the database?
            server_status = client.get_server_status()

            # Keep deleting songs while there are some...
            songs_remaining = True
            current_page    = 1
            progress_bar    = tqdm(
                desc=_('Deleting files'),
                total=server_status.songs,
                unit=_(' songs'))
            while songs_remaining:

                # Get a batch of songs...
                all_songs_list = client.get_all_songs(page=current_page, page_size=100)

                # No more songs left...
                if len(all_songs_list) == 0:
                    songs_remaining = False

                # Delete each one's song file...
                for song in all_songs_list:

                    # Submit request to server...
                    song_deleted = delete_song(
                        client,
                        song_id=song.id,
                        song_reference=song.reference,
                        delete_file_only=True)

                    # Update deletion counter...
                    if song_deleted:
                        total_deleted += 1

                    # Update progress bar...
                    progress_bar.update(1)

                # Advance to next page...
                current_page += 1

            # Done...
            progress_bar.close()
            success = True

        # User requested to delete all songs and their files...
        elif arguments.delete_all and not arguments.delete_file_only:

            # Prompt user to make sure they are certain they know what they are
            #  doing...
            verification = input(_('Are you sure you know what you are doing? Type \'YES\': '))
            if verification != _('YES'):
                sys.exit(1)

            # How many songs are currently in the database?
            server_status = client.get_server_status()

            # Keep deleting songs while there are some...
            songs_remaining = True
            progress_bar    = tqdm(
                desc=_('Deleting metadata and files'),
                total=server_status.songs,
                unit=_(' songs'))
            while songs_remaining:

                # Get a batch of songs. We can always start chomping at the
                #  first page because everything after it is shifted up the
                #  first page after being deleted...
                all_songs_list = client.get_all_songs(page=1, page_size=100)

                # No more songs left...
                if len(all_songs_list) == 0:
                    songs_remaining = False

                # Delete each one...
                for song in all_songs_list:

                    # Submit request to server...
                    song_deleted = delete_song(
                        client,
                        song_id=song.id,
                        song_reference=song.reference,
                        delete_file_only=False)

                    # Update deletion counter...
                    if song_deleted:
                        total_deleted += 1

                    # Update progress bar...
                    progress_bar.update(1)

            # Done...
            progress_bar.close()
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

    # Cleanup any resources...
    finally:

        # Dump any new output beginning on a new line...
        print('')

        # Cleanup progress bar, if one was constructed...
        if progress_bar:
            progress_bar.close()

    # Show deletion statistics...
    print(F'Deleted {total_deleted} successfully.')

    # If unsuccessful, bail...
    if not success:
        sys.exit(1)

    # Done...
    sys.exit(0)

# Entry point...
if __name__ == '__main__':
    main()

