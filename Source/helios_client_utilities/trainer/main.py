#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2024 Cartesian Theatre. All rights reserved.
#

# System imports...
import sys

# Gtk related imports...
import gi
from gi.repository import Gio

# Our imports...
import helios
from helios_client_utilities.trainer import *

# i18n...
import gettext
_ = gettext.gettext

# Main...
def main():

    # Construct application...
    application = TrainerApplication(application_id=get_application_id())

    # Run application and capture exit code...
    status = application.run(sys.argv)

    # Exit, reporting application exit code to system...
    sys.exit(status)

# Entry point...
if __name__ == '__main__':
    main()

