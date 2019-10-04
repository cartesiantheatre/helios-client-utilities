#!/bin/bash
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2019 Cartesian Theatre. All rights reserved.
#

# Bail on any errors...
set -e

echo "Try adding a song..."
helios-add-song --reference "some_reference" "/usr/share/games/lincity-ng/music/default/02 - Robert van Herk - City Blues.ogg"

echo "Try similarity match..."
helios-similar --file "/usr/share/games/lincity-ng/music/default/03 - Robert van Herk - Architectural Contemplations.ogg"

echo "OK"

