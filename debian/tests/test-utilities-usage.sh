#!/bin/bash
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2024 Cartesian Theatre. All rights reserved.
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
SONG_REFERENCE_A="REF_1"
SONG_REFERENCE_B="REF_2"
SONG_REFERENCE_C="REF_3"

# Sample list of songs that should be installed from the lincity-ng 
SAMPLE_SONG_A="/usr/share/games/lincity-ng/music/default/01 - pronobozo - lincity.ogg"
SAMPLE_SONG_B="/usr/share/games/lincity-ng/music/default/02 - Robert van Herk - City Blues.ogg"
SAMPLE_SONG_C="/usr/share/games/lincity-ng/music/default/03 - Robert van Herk - Architectural Contemplations.ogg"

# Treat all Python warnings as fatal errors...
export PYTHONWARNINGS="error,ignore::ResourceWarning"

# Verify helios-trainer modules load...
#  https://pygobject.readthedocs.io/en/latest/guide/testing.html
echo "*** Checking all modules load in helios-trainer(1) with --version"
helios-trainer --version

# Verify we can find the server via avahi-browse(1)...
echo "*** Verifying server status via avahi-browse(1)..."
avahi-browse --all --terminate | grep Helios

# Verify we can find the server via helios-status(1)...
echo "*** Verifying server status via helios-status(1)..."
helios-status --verbose

# Add a song...
echo "*** Adding a song..."
helios-add-song --reference "$SONG_REFERENCE_B" "$SAMPLE_SONG_B"

# Delete a song...
echo "*** Deleting a song..."
helios-delete-song --reference "$SONG_REFERENCE_B"

# Add same song back again...
echo "*** Adding song again..."
helios-add-song --reference "$SONG_REFERENCE_B" "$SAMPLE_SONG_B"

# Try downloading same song...
echo "*** Downloading song..."
helios-download-song --reference "$SONG_REFERENCE_B" --output foo.ogg

# Verify it hasn't changed...
echo "*** Verifying it is what we originally uploaded..."
cmp foo.ogg "$SAMPLE_SONG_B"

# Retrieve its metadata...
echo "*** Getting song metadata..."
helios-get-song --reference "$SONG_REFERENCE_B"

# Try modifying its metadata...
echo "*** Modify song metadata..."
helios-modify-song                  \
    --reference "$SONG_REFERENCE_B"   \
    --edit-file "$SAMPLE_SONG_A"    \
    --edit-artist "Pronobozo"       \
    --edit-title "Lincity"

# Batch import a list of songs from a CSV file...
echo "*** Batch import songs from CSV..."
helios-import-songs $(dirname $0)/sample_import_lincity.csv

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

# Batch import a list of songs from a CSV file again...
echo "*** Batch import songs from CSV..."
helios-import-songs $(dirname $0)/sample_import_lincity.csv

# Try adding two learning examples...
echo "*** Adding two learning examples..."
helios-learn add --anchor $SONG_REFERENCE_A --positive $SONG_REFERENCE_B --negative $SONG_REFERENCE_C
helios-learn add --anchor $SONG_REFERENCE_C --positive $SONG_REFERENCE_B --negative $SONG_REFERENCE_A

# Delete one of the learning examples...
echo "*** Deleting a learning example..."
helios-learn delete --anchor $SONG_REFERENCE_C --positive $SONG_REFERENCE_B --negative $SONG_REFERENCE_A

# Get the learning example...
echo "*** List all learning examples..."
helios-learn list

# Show a learning examples summary...
echo "*** Summarizing learning examples..."
helios-learn summary

# Purge all learning examples...
echo "*** Purging all learning examples..."
yes YES 2>/dev/null | helios-learn purge

# Purge the song database...
echo "*** Delete all songs..."
yes YES 2>/dev/null | helios-delete-song --delete-all

# TODO: Test helios-trainer
#  Use dogtail to test GUI in headless environment:
#  <https://gitlab.com/dogtail/dogtail/-/tree/master/examples/>

# Alert user all done...
echo "*** OK"

