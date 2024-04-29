#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2024 Cartesian Theatre. All rights reserved.
#

# System imports...
import os
import tempfile

# Helios...
import helios

# i18n...
import gettext
_ = gettext.gettext

# Match bundle class containing paths to a search key song on disk, its matches,
#  associated artwork, and metadata...
class MatchBundle:

    # Constructor...
    def __init__(self, total_matches: int):

        # Store arguments...
        self._total_matches = total_matches

        # Create a directory to contain all assets...
        self._root = tempfile.mkdtemp(prefix='helios_trainer_bundle_')

        # Create path to search key...
        _, self._search_key_path = tempfile.mkstemp(prefix='search_key_', dir=self._root)

        # List of paths to matches...
        self._matches_path_list = []

        # Create a path to each match...
        for index in range(0, self._total_matches):

            # Create path to match...
            _, match = tempfile.mkstemp(prefix=F'match_{index}_', dir=self._root)

            # Add to list...
            self._matches_path_list.append(match)

        # Byte array for search key artwork...
        self._search_key_artwork = None

        # Search key song object...
        self._search_key_song_object = None

        # List of byte arrays, one for each match's artwork...
        self._match_list_artwork = [None] * self._total_matches

        # List of song match objects...
        self._match_song_object_list = [None] * self._total_matches

    # Delete bundle...
    def cleanup(self):

        # Delete search key...
        self.delete_file(self._search_key_path)

        # Delete each file, if it exists on disk...
        for file in self._matches_path_list:
            self.delete_file(file)

        # Lastly try to delete the temporary directory containing the bundle...
        try:
            os.rmdir(self._root)

        # Ignore failures...
        except FileNotFoundError:
            pass

        # Clear root path...
        self._root = None

        # Clear matches list...
        self._matches_path_list.clear()

        # Clear artwork...
        self._search_key_artwork = None
        self._match_list_artwork = [None] * self._total_matches

        # Clear song objects...
        self._match_song_object_list = [None] * self._total_matches

    # Delete a file and don't complain if it's not found...
    def delete_file(self, path):

        # Try to delete file...
        try:
            os.remove(path)

        # If it didn't exist, don't worry about it...
        except FileNotFoundError:
            pass

    # Get path to a match...
    def get_match_path(self, index):
        return self._matches_path_list[index]

    # Get path to bundle root...
    def get_root_path(self):
        return self._root_path

    # Get path to search key...
    def get_search_key_path(self):
        return self._search_key_path

    # Get the search key artwork...
    def get_search_key_artwork(self):
        return self._search_key_artwork

    # Get the search key song object...
    def get_search_key_song_object(self):
        return self._search_key_song_object

    # Get the given match's artwork...
    def get_match_artwork(self, index: int):
        return self._match_list_artwork[index]

    # Get the given match's song object...
    def get_match_song_object(self, index):
        return self._match_song_object_list[index]

    # Get the total number of matches...
    def get_total_matches(self):
        return self._total_matches

    # Set the search key artwork...
    def set_search_key_artwork(self, artwork: bytes):
        self._search_key_artwork = artwork

    # Set the given match's artwork...
    def set_match_artwork(self, index: int, artwork: bytes):
        self._match_list_artwork[index] = artwork

    # Set the given match's song object...
    def set_match_song_object(self, index: int, song_object: helios.responses.StoredSong):
        self._match_song_object_list[index] = song_object

    # Set the search key song object...
    def set_search_key_song_object(self, song_object: helios.responses.StoredSong):
        self._search_key_song_object = song_object

    # Destructor...
    def __del__(self):

        # Cleanup disk usage...
        self.cleanup()

