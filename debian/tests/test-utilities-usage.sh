#!/bin/bash
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2021 Cartesian Theatre. All rights reserved.
#

# Bail on any errors...
set -e

# Use default temporary directory if non-assigned...
if [ -z ${AUTOPKGTEST_TMP+x} ]; then
    AUTOPKGTEST_TMP=/tmp
fi

# Change current working directory to temporary directory...
cd $AUTOPKGTEST_TMP

# Sample song reference to use during interaction with server...
SONG_REFERENCE="some_reference"

# Sample list of songs that should be installed from the lincity-ng 
SAMPLE_SONG_A="/usr/share/games/lincity-ng/music/default/01 - pronobozo - lincity.ogg"
SAMPLE_SONG_B="/usr/share/games/lincity-ng/music/default/02 - Robert van Herk - City Blues.ogg"
SAMPLE_SONG_C="/usr/share/games/lincity-ng/music/default/03 - Robert van Herk - Architectural Contemplations.ogg"

# Verify we can find the server via avahi-browse(1)...
echo "*** Verifying server status via avahi-browse(1)..."
avahi-browse --all --terminate | grep Helios

# Verify we can find the server via helios-status(1)...
echo "*** Verifying server status via helios-status(1)..."
helios-status --verbose

# Add a song...
echo "*** Adding a song..."
helios-add-song --reference "$SONG_REFERENCE" "$SAMPLE_SONG_B"

# Delete a song...
echo "*** Deleting a song..."
helios-delete-song --reference "$SONG_REFERENCE"

# Add same song back again...
echo "*** Adding song again..."
helios-add-song --reference "$SONG_REFERENCE" "$SAMPLE_SONG_B"

# Try downloading same song...
echo "*** Downloading song..."
helios-download-song --reference "$SONG_REFERENCE" --output foo.ogg

# Verify it hasn't changed...
echo "*** Verifying it is what we originally uploaded..."
cmp foo.ogg "$SAMPLE_SONG_B"

# Retrieve its metadata...
echo "*** Getting song metadata..."
helios-get-song --reference "$SONG_REFERENCE"

# Try modifying its metadata...
echo "*** Modify song metadata..."
helios-modify-song                  \
    --reference "$SONG_REFERENCE"   \
    --edit-file "$SAMPLE_SONG_A"    \
    --edit-artist "Pronobozo"       \
    --edit-title "Lincity"

# Batch import a list of songs from a CSV file...
echo "*** Batch import songs from CSV..."
helios-import-songs --max-errors 0 $(dirname $0)/sample_import_lincity.csv

# Perform a similarity match against local song external to catalogue...
echo "*** Trying similarity match against local song external to catalogue..."
helios-similar --file "$SAMPLE_SONG_C"

# Retrieve a random song....
echo "*** Querying for a single randomly selected song in catalogue..."
helios-get-song --random=1

#echo "*** Trying similarity match against external remote search key..."
#helios-similar --url "https://soundcloud.com/afterlifeofc/tone-depth-ibn-sina-2"

# Purge the song database...
echo "*** Delete all songs..."
yes YES 2>/dev/null | helios-delete-song --delete-all

# Alert user all done...
echo "*** OK"

