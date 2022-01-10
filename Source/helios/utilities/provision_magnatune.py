#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2021 Cartesian Theatre. All rights reserved.
#

# System imports...
import argparse
import base64
import getpass
import gzip
import itertools
import logging
import os
import random
import re
import sqlite3
import sys
import tempfile
import traceback
import urllib

# Other imports...
from helios.utilities import __version__
import keyring
import magic
import mutagen.flac
import mutagen.id3
import mutagen.mp4
import mutagen.oggvorbis
import PIL.Image
import requests
from tqdm import tqdm

# i18n...
import gettext
_ = gettext.gettext

# Add arguments specific to this utility to argument parser...
def add_arguments(argument_parser):

    # Define positional argument for catalogue file...
    argument_parser.add_argument(
        'output_directory',
        nargs='?',
        default=os.getcwd(),
        help=_('Path to output directory.'))

    # Define behaviour for --absolute-path...
    argument_parser.add_argument(
        '--absolute-path',
        action='store_true',
        default=False,
        dest='absolute_path',
        help=_('Write absolute path to song in generated CSV instead of just '
               'file name.'))

    # Define behaviour for --cached-sqlite...
    argument_parser.add_argument(
        '--cached-sqlite',
        dest='cached_sqlite_path',
        required=False,
        nargs='?',
        help=_('Path to locally cached SQLite database.'))

    # Define behaviour for --cover-artwork...
    argument_parser.add_argument(
        '--cover-artwork',
        action='store_true',
        default=False,
        dest='cover_artwork',
        help=_('If a song does not contain embedded cover art, ask Magnatune '
               'for it and then embed it in the file if supported.'))

    # Define behaviour for --cover-artwork-archive...
    argument_parser.add_argument(
        '--cover-artwork-archive',
        dest='cover_artwork_archive_path',
        required=False,
        nargs='?',
        help=_('Archive a copy of each song\'s cover art in here.'))

    # Define behaviour for --force-overwrite
    argument_parser.add_argument(
        '--force-overwrite',
        action='store_true',
        default=False,
        dest='force_overwrite',
        help=_('Force overwrite of all local songs with fresh download.'))

    # Define behaviour for --format...
    argument_parser.add_argument(
        '--format',
        choices=['wav', 'mp3', 'alac', 'vorbis'],
        default='vorbis',
        dest='format',
        help=_('Audio format of songs to download.'),
        nargs='?',
        required=False)

    # Define behaviour for --genre...
    argument_parser.add_argument(
        '--genre',
        choices=['classical', 'new-age', 'electronica', 'world', 'ambient',
                 'jazz', 'hip-hop', 'alt-rock', 'electro-rock', 'hard-rock'],
        default=None,
        dest='genre',
        help=_('Requested genre, or by default any.'),
        nargs='?',
        required=False)

    # Define behaviour for --maximum-errors...
    argument_parser.add_argument(
        '--maximum-errors',
        default=1,
        dest='maximum_errors',
        nargs='?',
        type=int,
        help=_('Maximum number of errors to tolerate before exiting. Defaults '
               'to one. Set to zero for unlimited non-fatal.'))

    # Define behaviour for --minimum-length...
    argument_parser.add_argument(
        '--minimum-length',
        default=0,
        dest='minimum_length',
        nargs='?',
        type=int,
        help=_('Only consider songs at least the given length. The default is '
               'zero, or any length.'))

    # Define behaviour for --output-csv...
    argument_parser.add_argument(
        '--output-csv',
        dest='output_csv',
        default=None,
        required=False,
        nargs='?',
        help=_('CSV file to be gemerated upon completion.'))

    # Define behaviour for --password...
    argument_parser.add_argument(
        '--password',
        dest='password',
        default=None,
        required=False,
        nargs='?',
        help=_('Password to authenticate as with remote Magnatune service.'))

    # Define behaviour for --random
    argument_parser.add_argument(
        '--random',
        action='store_true',
        default=False,
        dest='random',
        help=_('Randomly select songs to download. Requires --song-count.'))

    # Define behaviour for --song-count...
    argument_parser.add_argument(
        '--song-count',
        default=0,
        dest='song_count',
        nargs='?',
        type=int,
        help=_('Number of songs to attempt to download.'))

    # Define behaviour for --user...
    argument_parser.add_argument(
        '--user',
        default=None,
        dest='user',
        required=True,
        nargs='?',
        help=_('User to authenticate as with remote Magnatune service.'))

    # Define behaviour for --verbose
    argument_parser.add_argument(
        '--verbose',
        action='store_true',
        default=False,
        dest='verbose',
        help=_('Be verbose by showing additional information.'))

    # Define behaviour for --version...
    argument_parser.add_argument(
        '--version',
        action='version',
        version=get_version())

# Download a file over HTTP to either a file object or a file name...
def download_file(url, fileobj=None, filename=None, verify=False, authorization_dict=None):

    # Either a file object or a file name has to be provided...
    if fileobj is not None and filename is not None:
        raise Exception(_("Expected either a file object or a file name. Neither were provided."))

    # Initialize a requests' library session...
    session = requests.Session()

    # Construct an adaptor to automatically make three retry attempts on failed
    #  DNS lookups and connection timeouts...
    adapter = requests.adapters.HTTPAdapter(max_retries=3)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    # Progress bar to be allocated later...
    progress_bar = None

    # If credentials provided, use basic authentication as expected by Magnatune
    #  service...
    if authorization_dict is not None and ("user" in authorization_dict and "pass" in authorization_dict):
        session.auth=requests.auth.HTTPBasicAuth(
            authorization_dict['user'],
            authorization_dict['pass'])

    # Add some of our own custom headers...
    headers                 = {}
    headers['Accept']       = '*/*'
    headers['User-Agent']   = F'helios-provision-magnatune {get_version()}'
    session.headers.update(headers)

    # Try to perform download...
    try:

        # Make request to server...
        response = session.get(
            url,
            stream=True,
            verify=verify) # Whether to verify server certificate...

        # We reached the server. If we didn't get an expected response, raise an
        #  exception...
        response.raise_for_status()

        # Get total size of response body...
        total_size = int(response.headers.get('Content-Length'))

        # Show progress...
        progress_bar = tqdm(
            bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{rate_fmt}{postfix}]',
            leave=False,
            colour='#442f4f', # From Helios branding guidelines kit
            total=total_size,
            unit=_('bytes'),
            unit_scale=True)

        # User provided a file name instead of a file object. Open it...
        if filename is not None:
            fileobj = open(filename, "wb")

        # As each chunk streams into memory, write it out...
        for chunk in response.iter_content(chunk_size=8192):

            # But skip keep-alive chunks...
            if not chunk:
                continue

            # Append chunk to file...
            fileobj.write(chunk)

            # Advance progress...
            progress_bar.update(len(chunk))

    # Clean up...
    finally:

        # Deallocate progress bar...
        if progress_bar is not None:
            progress_bar.clear()
            progress_bar.close()

        # Close socket, adapter, and session...
        session.close()

        # Close file object, if we created it. Otherwise leave caller's alone
        #  because caller may still want to write to it...
        if filename and fileobj:
            fileobj.close()

    # Return all server headers...
    return response.headers

# Embed the given artwork in the given song...
def embed_artwork(song_path, artwork_path):

    # Detect MIME type of song and artwork to embed...
    song_mime_type      = magic.from_file(song_path, mime=True)
    artwork_mime_type   = magic.from_file(artwork_path, mime=True)

    # Load artwork as a PIL image object...
    artwork_pil = PIL.Image.open(artwork_path)

    # Get dimensions...
    width, height = artwork_pil.size

    # Get depth...
    mode_to_depth = {
        '1' : 1,
        'L' : 8,
        'P' : 8,
        'RGB' : 24,
        'RGBA' : 32,
        'CMYK' : 32,
        'YCbCr' : 24,
        'I' : 32,
        'F' : 32
    }
    depth = mode_to_depth[artwork_pil.mode]

    # Get artwork raw data...
    with open(artwork_path, "rb") as artwork_fileobj:
        artwork_data = artwork_fileobj.read()

    # This is an mp3...
    if song_mime_type == "audio/mpeg":

        # Load ID3 frame from song...
        tags = mutagen.id3.ID3(song_path)

        # Create an attached picture...
        apic = mutagen.id3.APIC(
            encoding=3,             # 3 is for UTF-8...
            mime=artwork_mime_type,
            type=3,                 # 3 means album front cover...
            desc=u'Cover',
            data=artwork_data)

        # Inject into the ID3 frame...
        tags.add(apic)

        # Write out to disk...
        tags.save(v2_version=3)

    # Apple lossless in M4A container...
    elif song_mime_type in ("audio/mp4", "audio/m4a", "video/mp4"):

        # Open song...
        mp4_file = mutagen.mp4.MP4(song_path)

        # Select cover atom image type...
        imageformat = None
        if artwork_mime_type == 'image/png':
            imageformat=mutagen.mp4.MP4Cover.FORMAT_PNG
        elif artwork_mime_type == "image/jpeg":
            imageformat=mutagen.mp4.MP4Cover.FORMAT_JPEG
        else:
            raise Exception(_(F"Unsupported image format {artwork_mime_type} for M4A cover atom."))

        # Inject a covr atom...
        mp4_file["covr"] = [ mutagen.mp4.MP4Cover(artwork_data, imageformat=imageformat) ]

        # Write out to disk...
        mp4_file.save()

    # Vorbis in Ogg container...
    elif song_mime_type in ("audio/ogg", "audio/vorbis", "application/ogg"):

        # Open song...
        vorbis_file             = mutagen.oggvorbis.OggVorbis(song_path)

        # Construct a picture...
        picture                 = mutagen.flac.Picture()
        picture.data            = artwork_data
        picture.type            = 0x03                  # Cover (front)
        picture.desc            = u"Cover (front)"      # Exact spelling important and case sensitive too
        picture.mime            = artwork_mime_type
        picture.width           = width
        picture.height          = height
        picture.depth           = depth

        # Encode to a bytes object...
        picture_data            = picture.write()
        base64_encoded_data     = base64.b64encode(picture_data)

        # Save as a base 64 encoded ASCII string...
        base64_string           = base64_encoded_data.decode("ascii")

        # Save string into file...
        vorbis_file["metadata_block_picture"] = [base64_string]

        # Write out to disk...
        vorbis_file.save()

    # Unknown file format...
    else:
        raise Exception(_(F"Don't know how to embed artwork in song of type {song_mime_type}."))

# Generate a unique Magnatune song reference based on the song's filename and
#  extension...
def get_magnatune_reference(filename_with_extension):

    # Split file name and extension...
    filename, extension = os.path.splitext(filename_with_extension)

    # Format song unique reference string...
    reduced_filename_with_extension = re.sub("[^0-9a-zA-Z]+", "_", filename_with_extension)
    reduced_filename_with_extension = reduced_filename_with_extension.upper()
    unique_reference = F"MAGNATUNE_{reduced_filename_with_extension}"

    # Return unique reference...
    return unique_reference

# Get utilities package version...
def get_version():
    return __version__.version

# Return boolean depending on whether the given path to a song contains embedded
#  artwork...
def is_artwork_embedded(song_path):

    # Detect MIME type of artwork...
    song_mime_type = magic.from_file(song_path, mime=True)

    # This is an mp3...
    if song_mime_type == "audio/mpeg":

        # Load ID3 frame...
        tags = mutagen.id3.ID3(song_path)

        # Check for attached pictures...
        apic_list = tags.getall("APIC")

        # If we found at least one, and it contains non-zero bytes...
        if len(apic_list) > 0 and len(apic_list[0].data) > 0:
            return True

    # Apple lossless in M4A container...
    elif song_mime_type in ("audio/mp4", "audio/m4a", "video/mp4"):

        # Load file...
        mp4_file = mutagen.mp4.MP4(song_path)

        # Get tags...
        m4a_tags = mp4_file.tags

        # Get list of cover art atoms...
        cover_atom_list = m4a_tags.get("covr")

        # Check to find one that has a format we recognize...
        for mp4_cover in cover_atom_list:

            # Empty length. Try next atom...
            if len(mp4_cover) == 0:
                continue

            # We recognize this format. We're good...
            if (mp4_cover.imageformat == mp4_cover.FORMAT_JPEG) or (mp4_cover.imageformat == mp4_cover.FORMAT_PNG):
                return True

    # Vorbis in Ogg container...
    elif song_mime_type in ("audio/ogg", "audio/vorbis", "application/ogg"):

        # Open file...
        vorbis_file = mutagen.oggvorbis.OggVorbis(song_path)

        # Try to find artwork in each metadata picture block...
        for base64_data in vorbis_file.get("metadata_block_picture", []):

            # Try and decode candidate block into binary. If unable to, try next
            #  block...
            try:
                decoded_data = base64.b64decode(base64_data)
            except (TypeError, ValueError):
                continue

            # We managed to decode something. Check to make sure its a picture
            #  of some kind, and if it isn't, try next block...
            try:
                mutagen.flac.Picture(decoded_data)
            except mutagen.flac.error:
                continue

            # Ok, we found a picture of some kind...
            return True

        # Some programs also write base64 encoded image data directly into the
        #  'coverart' field and sometimes with a corresponding mime type into
        #  the 'coverartmime' field...
        coverart_values = vorbis_file.get("coverart", [])
        coverart_mimes = vorbis_file.get("coverartmime", [])

        # Check for any cover art...
        for value, mime in itertools.zip_longest(coverart_values, coverart_mimes, fillvalue=u""):

            # Try to decode, and if not, try next coverart field...
            try:
                base64.b64decode(value.encode("ascii"))
            except (TypeError, ValueError):
                continue

            # We found some cover art...
            return True

    # Either nothing present, or didn't know on how to look for it...
    return False

# Select appropriate file extension for a Mangnatune download based on the
#  user's requested format...
def select_extension(requested_format):

    # File extension to recommend...
    extension = None

    # Raw uncompressed wave...
    if requested_format == "wav":
        extension = "wav"

    # High quality lossy VBR encoded MP3, but not lo-fi 128K that's also
    #  available from Magnatune...
    elif requested_format == "mp3":
        extension = "mp3" # This is a no-op because extension already this...

    # High quality Apple lossless encoded in an M4A container...
    elif requested_format == "alac":
        extension = "m4a"

    # High quality lossy Vorbis in Ogg container...
    elif requested_format == "vorbis":
        extension = "ogg"

    # Unknown...
    else:
        raise Exception(_("Unknown requested audio format."))

    # Return recommended file extension to caller...
    return extension

# Main function...
def main():

    # Initialize the argument parser...
    argument_parser = argparse.ArgumentParser(
        description=_('Download Magnatune catalogue and generate CSV for helios-import-songs(1).'))

    # Add arguments specific to this utility to argument parser...
    add_arguments(argument_parser)

    # Parse the command line...
    arguments = argument_parser.parse_args()

    # Setup logging...
    logging_format = "%(asctime)s: %(message)s"
    if arguments.verbose:
        logging.basicConfig(format=logging_format, level=logging.DEBUG, datefmt="%H:%M:%S")
    else:
        logging.basicConfig(format=logging_format, level=logging.INFO, datefmt="%H:%M:%S")

    # Success flag to determine exit code...
    success = False

    # Track how many non-fatal errors occurred...
    errors_remaining = arguments.maximum_errors

    # List of failure messages...
    error_messages = []

    # Connection handle for SQLite database...
    sqlite_connection = None

    # Temporary files and file descriptors to close on exit...
    temporary_fds       = []
    temporary_fileobjs  = []

    # Temporary file names to delete on exit...
    temporary_filenames = []

    # Create output directory, if not already...
    os.makedirs(name=arguments.output_directory, exist_ok=True)

    # A cover artwork directory was specified. Prepare for it...
    if arguments.cover_artwork_archive_path is not None:

        # If it's not an absolute path, convert it...
        if not os.path.isabs(arguments.cover_artwork_archive_path):
            arguments.cover_artwork_archive_path = os.path.abspath(arguments.cover_artwork_archive_path)

        # Create the path, if not already...
        os.makedirs(name=arguments.cover_artwork_archive_path, exist_ok=True)

        # Make sure it is writeable...
        if not os.access(arguments.cover_artwork_archive_path, os.W_OK):
            logging.error(_(F"Cover artwork archival directory is not writeable. Check permissions: {arguments.cover_artwork_archive_path}"))
            sys.exit(1)

    # Calculate absolute path to user's requested output directory, if not
    #  already...
    if not os.path.isabs(arguments.output_directory):
        arguments.output_directory = os.path.abspath(arguments.output_directory)

    # Make sure output path for songs is writeable...
    if not os.access(arguments.output_directory, os.W_OK):
        logging.error(_(F"Output directory is not writeable. Check permissions: {arguments.output_directory}"))
        sys.exit(1)

    # If the output CSV path isn't provided, set to default...
    if not arguments.output_csv:
        arguments.output_csv = os.path.join(arguments.output_directory, "magnatune.csv")

    # Make sure output CSV path is absolute path...
    arguments.output_csv = os.path.abspath(arguments.output_csv)

    # Make sure output CSV file is in a writeable directory...
    if not os.access(os.path.dirname(arguments.output_csv), os.W_OK):
        logging.error(_(F"CSV output directory is not writeable. Check permissions: {os.path.dirname(arguments.output_csv)}"))
        sys.exit(1)

    # Create CSV output parent directory, if not already...
    os.makedirs(name=os.path.dirname(arguments.output_csv), exist_ok=True)

    # Remove any artwork downloaded on exit...
    temporary_filenames.append(os.path.join(arguments.output_directory, "artwork.tmp"))

    # Relative location of error log, if one is generated...
    error_log_path = os.path.join(arguments.output_directory, "errors.log")

    # Remove old error log, if it existed...
    if os.path.exists(error_log_path):
        os.remove(error_log_path)

    # Make sure user only requests --random with a specific song count...
    if arguments.random and arguments.song_count == 0:
        logging.error(_("You must specify a --song-count when requesting a --random song selection."))
        sys.exit(1)

    # Try to download Magnatune SQLite database, requested songs, and generate
    #  CSV...
    try:

        # If password was not already provided on the command line...
        if arguments.password is None:

            # Try querying system keyring...
            try:
                keyring_password = keyring.get_password("helios-provision-magnatune", arguments.user)

            # Problem initializing the keyring...
            except keyring.errors.InitError as some_exception:
                raise Exception(F_("Unable to initialize the keyring: {str(some_exception)}"))

            # If found in system keyring, use it...
            if keyring_password:
                arguments.password = keyring_password

            # Not found in system keyring. Prompt user for it...
            else:
                arguments.password = getpass.getpass(prompt=_(F'Enter Magnatune passphrase for user {arguments.user}: '))

        # Try updating keyring cache...
        try:
            keyring.set_password("helios-provision-magnatune", arguments.user, arguments.password)

        # Failed to unlock the keyring. This is not a fatal error...
        except keyring.errors.KeyringLocked:
            logging.warning(_("Unable to cache passphrase in locked keyring..."))

        # If a local cached copy of the Magnatune SQLite database was provided,
        #  use it instead of downloading...
        if arguments.cached_sqlite_path:

            # Log opening local database...
            logging.info(_(F"Opening local Magnatune SQLite database: {arguments.cached_sqlite_path}"))

            # Get the file extension for the database...
            sqlite_extension = os.path.splitext(arguments.cached_sqlite_path)[1]

            # If the database is compressed, decompress...
            if sqlite_extension.upper() == ".GZ":

                # Create a temp file for the decompressed version...
                [decompressed_fd, sqlite_tempfile_name] = tempfile.mkstemp(
                    prefix="helios_provision_magnatune_")

                # Remember to cleanup this file descriptor later and to delete
                #  the file itself...
                temporary_fds.append(decompressed_fd)
                temporary_filenames.append(sqlite_tempfile_name)

                # Decompress data to tempfile...
                with gzip.GzipFile(arguments.cached_sqlite_path, 'rb') as compressed_stream:

                    # Decompress stream...
                    decompressed_data = compressed_stream.read()

                    # Write out to disk...
                    os.write(decompressed_fd, decompressed_data)

                    # Remember the path for where the decompressed file is...
                    arguments.cached_sqlite_path = sqlite_tempfile_name

            # Open database...
            sqlite_connection = sqlite3.connect(
                database=F"file:{arguments.cached_sqlite_path}?mode=ro",
                uri=True)

        # Otherwise download from remote server...
        else:

            # Log downloading remote database...
            logging.info(_("Retrieving Magnatune catalogue index..."))

            # Create a tempfile object for the downloaded compressed database...
            [compressed_tempfilefd, compressed_tempfilename] = tempfile.mkstemp()

            # Remember to close it later and to delete it...
            temporary_fds.append(compressed_tempfilefd)
            temporary_filenames.append(compressed_tempfilename)

            # Download database and decompress it into RAM...
            response_headers = download_file(
                url="http://he3.magnatune.com/info/sqlite_normalized.db.gz",
                filename=compressed_tempfilename)

            # Show last modified date...
            logging.info(_(F"Last modified: {response_headers.get('Last-Modified')}"))

            # Create another tempfile object for the decompressed database and
            #  remember to clean it up too later...
            [decompressed_tempfilefd, decompressed_tempfilename] = tempfile.mkstemp(
                prefix="helios_provision_magnatune_")

            # Remember to close it later and to delete it...
            temporary_fds.append(decompressed_tempfilefd)
            temporary_filenames.append(decompressed_tempfilename)

            # Open the compressed stream through the gzip interface...
            with gzip.open(compressed_tempfilename, "rb") as compressed_stream:

                # Decompress all of it...
                decompressed_data = compressed_stream.read()

                # Save it to disk...
                os.write(decompressed_tempfilefd, decompressed_data)

            # Open database from disk...
            sqlite_connection = sqlite3.connect(
                database=F"file:{decompressed_tempfilename}?mode=ro",
                uri=True)

        # Get cursor to perform queries...
        cursor = sqlite_connection.cursor()

        # Count how many songs are in it...
        (catalogue_size, ) = cursor.execute("SELECT COUNT(*) FROM songs;").fetchone()
        logging.info(_(F"Catalogue contains a total of {catalogue_size} songs..."))

        # Total number of songs to request from Magnatune. Will be updated...
        total_requested = 0

        # Total eligible songs, which is a subset of the total catalogue size.
        #  Will be updated...
        total_eligible = 0

        # Get a list of all available songs from database...
        query = cursor.execute(
        """
            SELECT songs.song_id AS song_id, artists.name AS artist, albums.name AS album, genres.name AS genre, songs.duration as duration, songs.mp3 as filename
            FROM songs
            INNER JOIN albums ON songs.album_id = albums.album_id
            INNER JOIN artists ON albums.artist_id = artists.artists_id
            INNER JOIN genres_albums ON genres_albums.album_id = albums.album_id
            INNER JOIN genres ON genres.genre_id = genres_albums.genre_id
            ORDER BY songs.song_id;
        """)
        songs = query.fetchall()

        # Remove all those that don't match the user's requested genre, if
        #  specified...
        if arguments.genre:

            # Convert command line genre parameter to format used in database...
            genre_column = arguments.genre.replace("-", " ").title()

            # Set of song IDs to keep...
            song_ids_to_keep = set()

            # Each song can be listed multiple times since it can belong to
            #  multiple genres. If we find that the song is tagged with the
            #  requested genre, take note of the song's ID...
            for (song_id, artist, album, genre, duration, filename) in songs:
                if genre_column == genre:
                    song_ids_to_keep.add(song_id)

            # Now take a second pass through list and remove any song that
            #  doesn't have a song ID in the keep list...
            kept_songs = []
            for index, (song_id, artist, album, genre, duration, filename) in enumerate(songs):

                # If song had a matching genre tag, keep it...
                if song_id in song_ids_to_keep:

                    # Copy song to preservation list...
                    kept_songs.append(songs[index])

                    # Remove song ID from song IDs to check against in the
                    #  future to ensure we have only the song listed once, no
                    #  matter how many genres it was tagged with...
                    song_ids_to_keep.remove(song_id)

            # Overwrite the old songs list with the trimmed one...
            songs = kept_songs

        # Remove any duplicate entries of the same song since it can be tagged
        #  with multiple genres...
        song_ids_to_keep = set()
        kept_songs = []
        for index, (song_id, artist, album, genre, duration, filename) in enumerate(songs):

            # If we haven't already seen this song, add it to the preservation
            #  list...
            if song_id not in song_ids_to_keep:
                song_ids_to_keep.add(song_id)
                kept_songs.append(songs[index])

        # Overwrite the old songs list with the trimmed one...
        songs = kept_songs

        # Remove all those that don't meet a minimum duration, if specified...
        if arguments.minimum_length:

            # List of songs to keep...
            kept_songs = []

            # Check duration of each song...
            for index, (song_id, artist, album, genre, duration, filename) in enumerate(songs):

                # If duration is at least required minimum length, then add it
                #  to the preservation list...
                if duration >= arguments.minimum_length:
                    kept_songs.append(songs[index])

            # Overwrite the old songs list with the trimmed one...
            songs = kept_songs

        # Number of songs remaining is the total eligble...
        total_eligible = len(songs)

        # If user requested an exact number of songs, make sure there are at
        #  least that many eligible...
        if arguments.song_count > total_eligible:
            raise Exception(_(F"You requested {arguments.song_count} songs, but there were only {total_eligible} eligible of a total catalogue size of {catalogue_size}..."))

        # If user wants all of them, set to size of catalogue...
        if arguments.song_count == 0:
            total_requested = total_eligible

        # Otherwise set to requested amount...
        else:
            total_requested = arguments.song_count

        # Create a human readable version of the requested genre for logging...
        logged_genre = arguments.genre
        if logged_genre is None:
            logged_genre = "any"

        # If the user only wants a subset and requested random selection,
        #  shuffle it...
        if (arguments.song_count < total_eligible) and arguments.random:
            random.shuffle(songs)

        # Log total songs requested, noting whether we're going to select
        #  randomly...
        if arguments.random:
            logging.info(_(F"Retrieve {total_requested} random songs of {logged_genre} genre..."))
        else:
            logging.info(_(F"Retrieving {total_requested} songs of {logged_genre} genre..."))

        # Discard any songs beyond the total requested....
        del songs[total_requested:]

        # List of songs that were successfully downloaded that need to go in the
        #  generated CSV...
        downloaded_songs = []

        # Fetch each requested songs...
        for index, (song_id, artist, album, genre, duration, filename_with_extension) in enumerate(songs):

            # Split file name and extension...
            filename, extension = os.path.splitext(filename_with_extension)

            # Change file extension if required based on user's requested
            #  format...
            extension = select_extension(arguments.format)

            # Generate new file name...
            filename_with_extension = F"{filename}.{extension}"

            # Save it back in list so that when we write out paths to CSV, the
            #  correct file extension is saved...
            songs[index] = (song_id, artist, album, genre, duration, filename_with_extension)

            # Escape URL components so it is properly URL encoded...
            escaped_artist = urllib.parse.quote(artist)
            escaped_album = urllib.parse.quote(album)
            escaped_filename_with_extension = urllib.parse.quote(filename_with_extension)

            # Format complete URL to download...
            url = F"http://download.magnatune.com/music/{escaped_artist}/{escaped_album}/{escaped_filename_with_extension}"

            # Format complete output path...
            output_path = os.path.join(arguments.output_directory, filename_with_extension)

            # Try to download the song, and possibly artwork too if requested...
            try:

                # If we were asked to archive a copy of all available cover
                #  artwork, do it...
                if arguments.cover_artwork_archive_path is not None:

                    # List of available dimensions from Magnatune...
                    available_square_dimensions = [50, 75, 100, 160, 200, 300, 600, 1400]

                    # Do it for each available square dimension...
                    for dimension in available_square_dimensions:

                        # Format url to cover artwork...
                        artwork_url = F"http://he3.magnatune.com/music/{urllib.parse.quote(artist)}/{urllib.parse.quote(album)}/cover_{dimension}.jpg"

                        # Generate a unique reference to the song based on its
                        #  filename and extension...
                        unique_reference = get_magnatune_reference(filename_with_extension)

                        # Construct path to local download location for artwork...
                        artwork_output_path = os.path.join(arguments.cover_artwork_archive_path, F"{unique_reference}_{dimension}x{dimension}.jpg")

                        # If the file already exists, skip it...
                        if os.path.exists(artwork_output_path):
                            logging.info(F"[{song_id}] Skipping song {index + 1}/{total_requested}: Already archived {dimension}x{dimension} album artwork...")
                            continue

                        # Otherwise log what we are about to download...
                        logging.info(F"[{song_id}] Downloading song {index + 1}/{total_requested}: Archiving {dimension}x{dimension} album artwork...")

                        # If anything unexpected happens before file download is
                        #  complete, be sure to delete corrupt file...
                        temporary_filenames.append(artwork_output_path)

                        # Download artwork...
                        download_file(url=artwork_url, filename=artwork_output_path)

                        # Don't delete file on exit, now that we have all of it...
                        temporary_filenames.remove(artwork_output_path)

                # If user requested not to overwrite already existing songs, and
                #  this song has already been downloaded...
                if not arguments.force_overwrite and os.path.isfile(output_path):

                    # Log it...
                    logging.info(F"[{song_id}] Skipping song {index + 1}/{total_requested}: {filename_with_extension}")

                    # Remember add the song to the successfully downloaded list so
                    #  it is added to the generated CSV later...
                    downloaded_songs.append(songs[index])

                    # Skip it...
                    continue

                # Log what we are about to download...
                logging.info(F"[{song_id}] Downloading song {index + 1}/{total_requested}: {filename_with_extension}")

                # If anything unexpected happens before file download is
                #  complete, be sure to delete corrupt file...
                temporary_filenames.append(output_path)

                # Download song...
                download_file(
                    url=url,
                    filename=output_path,
                    authorization_dict={'user' : arguments.user, 'pass' : arguments.password})

                # Don't delete file on exit, now that we have all of it...
                temporary_filenames.remove(output_path)

                # If we were asked to embed cover artwork, and it's not already
                #  present in the song we just downloaded, embed it...
                if arguments.cover_artwork and not is_artwork_embedded(song_path=output_path):

                    # Format url to high resolution cover artwork, if we need to fetch it...
                    artwork_url = F"http://he3.magnatune.com/music/{urllib.parse.quote(artist)}/{urllib.parse.quote(album)}/cover_1400.jpg"

                    # Construct path to local download location for artwork...
                    artwork_output_path = os.path.join(arguments.output_directory, "artwork.tmp")

                    # Generate a unique reference to the song based on its
                    #  filename and extension...
                    unique_reference = get_magnatune_reference(filename_with_extension)

                    # Construct path to potentially extant already archived copy of the artwork...
                    archived_output_path = os.path.join(arguments.cover_artwork_archive_path, F"{unique_reference}_1400x1400.jpg")

                    # Check if the high resolution was already archived to prevent double download...
                    if os.path.exists(archived_output_path):

                        # Log that we are not about to download...
                        logging.info(F"[{song_id}] Skipping song {index + 1}/{total_requested}: High resolution album artwork already archived. Will embed...")

                        # Use path to archived artwork for embedding...
                        artwork_output_path = archived_output_path

                    # Otherwise if it has not been downloaded already...
                    else:

                        # Log what we are about to download...
                        logging.info(F"[{song_id}] Downloading song {index + 1}/{total_requested}: High resolution album artwork missing. Will embed...")

                        # Download artwork...
                        download_file(url=artwork_url, filename=artwork_output_path)

                    # Embed artwork...
                    embed_artwork(song_path=output_path, artwork_path=artwork_output_path)

                    # Delete temporary artwork file if it wasn't in the archived folder...
                    if not os.path.samefile(archived_output_path, artwork_output_path):
                        os.remove(artwork_output_path)

                # Remember add the song to the successfully downloaded list so
                #  it is added to the generated CSV later...
                downloaded_songs.append(songs[index])

            # User trying to abort. Propagate exception up...
            except KeyboardInterrupt as some_exception:
                raise some_exception

            # Check if this was a fatal error...
            except requests.exceptions.HTTPError as some_exception:

                # Failure to authenticate...
                if some_exception.response.status_code == 401:

                    # Format error...
                    message = _(F"[{song_id}] Error: Bad username or password...")

                    # Notify user now...
                    logging.error(message)

                    # ...and again later when we are ready to exit...
                    error_messages.append(message)

                # Something else...
                else:

                    # Format error...
                    message = _(F"[{song_id}] Error: {str(some_exception)}")

                    # Notify user now...
                    logging.error(message)

                    # ...and again later when we are ready to exit...
                    error_messages.append(message)

                # Decrement remaining permissible errors...
                errors_remaining -= 1

            # Connection problem...
            except Exception as some_exception:

                # Format error...
                message = _(F"{filename_with_extension}: {str(some_exception)}")

                # Notify user now...
                logging.error(_(F"Error: {message}"))

                # ...and again later when we are ready to exit...
                error_messages.append(message)

                # Decrement remaining permissible errors...
                errors_remaining -= 1

                # Dump stack trace...
                (exception_type, exception_value, exception_traceback) = sys.exc_info()
                traceback.print_tb(exception_traceback)

            # Things to do after each download or if a problem occurs during
            #  transfer...
            finally:

                # If no more permissible errors remaining, abort...
                if (errors_remaining <= 0) and (arguments.maximum_errors != 0):
                    raise Exception(_(F"Maximum errors reached (set to {arguments.maximum_errors}). Aborting..."))

        # Log what we are about to do next...
        logging.info(_(F"Generating CSV of {len(downloaded_songs)} songs: {arguments.output_csv}"))

        # Write out CSV contents to user's selected output file...
        with open(arguments.output_csv, "w") as file:

            # Start by emitting the column fields...
            print("reference,path", file=file)

            # Set that will be used to make sure each song reference is truly
            #  unique...
            unique_references = set()

            # Write out each song, line by line...
            for index, (song_id, artist, album, genre, duration, filename_with_extension) in enumerate(downloaded_songs):

                # Get song file name...
                output_path = filename_with_extension

                # If user requested absolute paths, convert accordingly...
                if arguments.absolute_path:
                    output_path = os.path.join(arguments.output_directory, filename_with_extension)

                # Format song unique reference string...
                unique_reference = get_magnatune_reference(filename_with_extension)

                # Check if the song reference wasn't actually unique...
                if unique_reference in unique_references:

                    # Format warning...
                    message = _(F"Non-unique song reference \"{unique_reference}\" for song ID {song_id}...")

                    # Notify user now...
                    logging.warning(_(F"Warning: {message}"))

                    # ...and again later when we are ready to exit...
                    error_messages.append(message)

                # Otherwise add it to the set of unique references so we can
                #  verify subsequent songs all have unique references too...
                else:
                    unique_references.add(unique_reference)

                # Format line for CSV...
                current_line = F"{unique_reference},{output_path}"

                # Write out line to CSV...
                print(current_line, file=file)

        # Determine how we will exit...
        success = (arguments.maximum_errors == 0 or (errors_remaining == arguments.maximum_errors))

    # User trying to abort...
    except KeyboardInterrupt:
        print(_('\nAborting, please wait a moment...'))
        success = False

    # Some other kind of exception...
    except Exception as some_exception:
        logging.info(_(f"Error: {str(some_exception)}"))

    # Cleanup...
    finally:

        # If there were any failures, log them...
        if len(error_messages) > 0:

            # Notify user...
            print(_(F"Warnings or failures for {len(error_messages)} songs: "))

            # Try to open a log file...
            try:
                log_file = open(error_log_path, "w")

            # Failed. Let user know...
            except OSError:
                print(_("Could not save failed import list to current working directory."))

            # Show each song's error message...
            for current_error_message in error_messages:

                # Save to log file if opened...
                if log_file:
                    log_file.write(F"{current_error_message}\n")

                # Show on stderr as well...
                print(F"  {current_error_message}")

            # Close log file if open...
            if log_file:
                log_file.close()

        # Close Magnatune database...
        if sqlite_connection:
            sqlite_connection.close()

        # Close all temporary file descriptors...
        for file_descriptor in temporary_fds:
            os.close(file_descriptor)

        # Close all temporary file objects...
        for fileobj in temporary_fileobjs:
            fileobj.close()

        # Delete any file that were supposed to be deleted on exit...
        for filename in temporary_filenames:

            # Delete file...
            try:
                os.remove(filename)

            # If it didn't exist, don't worry about it...
            except FileNotFoundError:
                pass

    # Exit with status code based on whether we were successful or not...
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

# Entry point...
if __name__ == '__main__':

    # Run main function...
    main()
