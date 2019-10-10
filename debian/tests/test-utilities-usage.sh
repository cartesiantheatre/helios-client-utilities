#!/bin/bash
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2019 Cartesian Theatre. All rights reserved.
#

# Bail on any errors...
set -e

SONG_REFERENCE="some_reference"

SAMPLE_SONG_A="/usr/share/games/lincity-ng/music/default/01 - pronobozo - lincity.ogg"
SAMPLE_SONG_B="/usr/share/games/lincity-ng/music/default/02 - Robert van Herk - City Blues.ogg"
SAMPLE_SONG_C="/usr/share/games/lincity-ng/music/default/03 - Robert van Herk - Architectural Contemplations.ogg"

if [ -z ${AUTOPKGTEST_TMP+x} ]; then
    AUTOPKGTEST_TMP=/tmp
fi

cd $AUTOPKGTEST_TMP

echo "*** Verifying server status..."
helios-status

echo "*** Adding a song..."
helios-add-song --reference "$SONG_REFERENCE" "$SAMPLE_SONG_B"

echo "*** Deleting a song..."
helios-delete-song --reference "$SONG_REFERENCE"

echo "*** Adding song again..."
helios-add-song --reference "$SONG_REFERENCE" "$SAMPLE_SONG_B"

echo "*** Downloading song..."
helios-download-song --reference "$SONG_REFERENCE" --output foo.ogg && rm foo.ogg

echo "*** Getting song metadata..."
helios-get-song --reference "$SONG_REFERENCE"

echo "*** Modify song metadata..."
helios-modify-song                  \
    --reference "$SONG_REFERENCE"   \
    --edit-file "$SAMPLE_SONG_A"    \
    --edit-artist "Pronobozo"       \
    --edit-title "Lincity"

echo "*** Batch import songs from CSV..."
helios-import-songs --max-errors 0 $(dirname $0)/sample_import_lincity.csv

#echo "*** Trying similarity match against external local file..."
helios-similar --file "$SAMPLE_SONG_C"

#echo "*** Trying similarity match against external remote search key..."
#helios-similar --url "https://soundcloud.com/afterlifeofc/tone-depth-ibn-sina-2"

echo "*** Delete all songs..."
yes YES 2>/dev/null | helios-delete-song --delete-all

echo "*** OK"

