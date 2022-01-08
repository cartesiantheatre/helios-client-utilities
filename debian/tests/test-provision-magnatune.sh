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

# Treat all Python warnings as fatal errors...
export PYTHONWARNINGS="error,ignore::ResourceWarning"

# Verify we can find the server via avahi-browse(1)...
echo "*** Verifying server status via avahi-browse(1)..."
avahi-browse --all --terminate | grep Helios

# Verify we can find the server via helios-status(1)...
echo "*** Verifying server status via helios-status(1)..."
helios-status --verbose

# Get Magnatune authentication credentials sources from shell script generated
#  by helios-autopkgtest package's preinst maintainer script...
. /tmp/magnatune_credentials.sh

# For instructions on getting keyring in helios-provision-magnatune(1) to work
#  on headless systems, see the following...
#  <https://github.com/jaraco/keyring#using-keyring-on-headless-linux-systems>

# Start a D-Bus session...
dbus-run-session -- sh

# Create a keyring using a dummy password...
gnome-keyring-daemon --unlock <<EOF
dummypassword
EOF

# Download and prepare a catalogue from Magnatune of five random Ogg/Vorbis
#  songs, each a minimum of 2 minutes in length, with embedded artwork if none
#  found, and authenticating with the remote service as the cartesian_theatre
#  user...
helios-provision-magnatune                                                      \
    --verbose                                                                   \
    --user $MAGNATUNE_USER                                                      \
    --password $MAGNATUNE_PASSWORD                                              \
    --format vorbis                                                             \
    --cover-artwork                                                             \
    --cover-artwork-archive Output/Artwork                                      \
    --song-count 5                                                              \
    --random                                                                    \
    --minimum-length 120                                                        \
    --absolute-path                                                             \
    Output/Songs

# Batch import the generated CSV catalogue...
echo "*** Batch import songs from Magnatune CSV..."
helios-import-songs Output/magnatune.csv

# Purge the song database...
echo "*** Delete all songs..."
yes YES 2>/dev/null | helios-delete-song --delete-all

# Alert user all done...
echo "*** OK"

