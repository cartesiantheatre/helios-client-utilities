#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2024 Cartesian Theatre. All rights reserved.
#

# System imports...

# Gtk related imports...
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gio, Gtk, GLib

# Helios...
import helios
from helios_client_utilities.trainer import *

# i18n...
import gettext
_ = gettext.gettext

# Stack page class...
class StackPage:

    # Constructor...
    def __init__(self, application_window, name, title):

        # Store reference to application window...
        self._application_window = application_window

        # Store reference to application...
        self._application = application_window.get_application()

        # Store page name and title...
        self._name  = name
        self._title = title

        # This will contain the sizer the application window will use to contain
        #  all of this page's widgets...
        self._sizer = None

    # Add page to stack...
    def add_to_stack(self, stack):
        stack.add_titled(self.get_sizer(), self.get_name(), self.get_title())

    # Get the page name...
    def get_name(self):
        return self._name

    # Get the title...
    def get_title(self):
        return self._title

    # Return top level sizer to caller which contains all of its children...
    def get_sizer(self):
        return self._sizer

