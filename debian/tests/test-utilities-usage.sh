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
SAMPLE_SONG_A="/usr/share/lincity-ng/music/default/01 - pronobozo - lincity.ogg"
SAMPLE_SONG_B="/usr/share/lincity-ng/music/default/02 - Robert van Herk - City Blues.ogg"
SAMPLE_SONG_C="/usr/share/lincity-ng/music/default/03 - Robert van Herk - Architectural Contemplations.ogg"

# Path to Magnatune minimal CSV catalogue...
MAGNATUNE_MINIMAL_CSV=/usr/share/helios-magnatune-minimal/magnatune-minimal.csv

# Treat all Python warnings as fatal errors...
export PYTHONWARNINGS="error,ignore::ResourceWarning"

# Verify we can find the server via avahi-browse(1)...
echo "*** Verifying server status via avahi-browse(1)..."
avahi-browse --all --terminate | grep Helios

# Verify we can find the server via helios-status(1)...
echo "*** Verifying server status via helios-status(1)..."
helios-status --host localhost --verbose

# Add a song...
echo "*** Adding a song..."
helios-add-song --host localhost --reference "$SONG_REFERENCE_B" "$SAMPLE_SONG_B"

# Delete a song...
echo "*** Deleting a song..."
helios-delete-song --host localhost --reference "$SONG_REFERENCE_B"

# Add same song back again...
echo "*** Adding song again..."
helios-add-song --host localhost --reference "$SONG_REFERENCE_B" "$SAMPLE_SONG_B"

# Try downloading same song...
echo "*** Downloading song..."
helios-download-song --host localhost --reference "$SONG_REFERENCE_B" --output foo.ogg

# Verify it hasn't changed...
echo "*** Verifying it is what we originally uploaded..."
cmp foo.ogg "$SAMPLE_SONG_B"

# Retrieve its metadata...
echo "*** Getting song metadata..."
helios-get-song --host localhost --reference "$SONG_REFERENCE_B"

# Try modifying its metadata...
echo "*** Modify song metadata..."
helios-modify-song                                                              \
    --host localhost                                                            \
    --reference "$SONG_REFERENCE_B"                                             \
    --edit-file "$SAMPLE_SONG_A"                                                \
    --edit-artist "Pronobozo"                                                   \
    --edit-title "Lincity"

# Batch import a list of songs from a CSV file...
echo "*** Batch import songs from CSV..."
helios-import-songs --host localhost $(dirname $0)/sample_import_lincity.csv

# Perform a similarity match against local song external to catalogue...
echo "*** Trying similarity match against local song external to catalogue..."
helios-similar --host localhost --file "$SAMPLE_SONG_C"

# Retrieve a random song....
echo "*** Querying for a single randomly selected song in catalogue..."
helios-get-song --host localhost --random=1

#echo "*** Trying similarity match against external remote search key..."
#helios-similar --host localhost --url "https://soundcloud.com/afterlifeofc/tone-depth-ibn-sina-2"

# Purge the song database...
echo "*** Delete all songs..."
yes YES 2>/dev/null | helios-delete-song --host localhost --delete-all

# Batch import a list of songs from a CSV file again...
echo "*** Batch import songs from small CSV..."
helios-import-songs --host localhost $(dirname $0)/sample_import_lincity.csv

# Save the current learning model and print it...
echo "*** Saving the current learning model:"
helios-learn --host localhost save-model learning_model.hml
cat learning_model.hml

# Delete the current learning model...
echo "*** Deleting the current learning model..."
helios-learn --host localhost delete-model

# Load the previous learning model...
echo "*** Restoring learning model:"
helios-learn --host localhost load-model learning_model.hml
rm learning_model.hml

# Try adding two learning examples...
echo "*** Adding two learning examples..."
helios-learn --host localhost add-example --anchor $SONG_REFERENCE_A --positive $SONG_REFERENCE_B --negative $SONG_REFERENCE_C
helios-learn --host localhost add-example --anchor $SONG_REFERENCE_C --positive $SONG_REFERENCE_B --negative $SONG_REFERENCE_A

# Delete one of the learning examples...
echo "*** Deleting a learning example..."
helios-learn --host localhost delete-example --anchor $SONG_REFERENCE_C --positive $SONG_REFERENCE_B --negative $SONG_REFERENCE_A

# Get the learning example...
echo "*** List all learning examples..."
helios-learn --host localhost list-examples

# Show a learning examples summary...
echo "*** Summarizing learning examples..."
helios-learn --host localhost summary

# Purge all learning examples...
echo "*** Purging all learning examples..."
yes YES 2>/dev/null | helios-learn --host localhost purge-examples

# Purge the song database...
echo "*** Delete all songs..."
yes YES 2>/dev/null | helios-delete-song --host localhost --delete-all

# Try importing a larger catalogue...
echo "*** Batch import songs from larger CSV, $MAGNATUNE_MINIMAL_CSV"
helios-import-songs --host localhost $MAGNATUNE_MINIMAL_CSV

# Purge the song database...
echo "*** Delete all songs..."
yes YES 2>/dev/null | helios-delete-song --host localhost --delete-all

# Alert user all done...
echo "*** OK"

