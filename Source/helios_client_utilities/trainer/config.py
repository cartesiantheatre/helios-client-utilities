#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2024 Cartesian Theatre. All rights reserved.
#

# System imports...
import getpass
import importlib_resources
import os
import pwd
import sys

# Gdk imports...
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gtk, Gdk

# Helios imports...
import helios_client_utilities.__version__ as __version__

# i18n...
import gettext
_ = gettext.gettext


# Get application ID...
def get_application_id():
    return "com.cartesiantheatre.helios_trainer"

# Get application name...
def get_application_name():
    return _("Helios Trainer")

# Return path to application data directory...
def get_data_dir():

    # Are we running in a virtual environment?
    if is_venv():

        # Construct path to local tree development data directory...
        data_dir = os.path.abspath(importlib_resources.files('helios_client_utilities').joinpath('../../Data/share/applications/helios-trainer'))

        # This path should exist or something is very wrong...
        if not os.path.exists(data_dir):
            raise FileNotFoundError(filename=data_dir)

        # Return path...
        return data_dir

    # Otherwise we must use the application data directory...
    else:

        # Otherwise try looking for system application data directory per FHS...
        data_dir = '/usr/share/applications/helios-trainer/'

        # This path should exist or something is very wrong...
        if not os.path.exists(data_dir):
            raise FileNotFoundError(filename=data_dir)

        # Return path...
        return data_dir

# Set path to icon theme search path if running in a virtual environment. This
#  ensures icons still load outside of a proper Debian package...
def set_icon_theme_search():

    # If we're not running in a virtual environment so use system default...
    if not is_venv():
        return

    # Construct path to local tree development icon directory...
    icon_dir = os.path.abspath(importlib_resources.files('helios_client_utilities').joinpath('../../Data/share/icons'))

    # This path should exist or something is very wrong...
    if not os.path.exists(icon_dir):
        raise FileNotFoundError(filename=icon_dir)

    # Get default icon theme...
    icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())

    # Add local icon directory to search path...
    icon_theme.add_search_path(icon_dir)

# Get application configuration directory...
def get_config_dir():

    # Find home directory...
    home_directory = os.path.expanduser('~')

    # Construct application configuration directory...
    config_dir = os.path.join(home_directory, '.config', 'helios-trainer')

    # If it doesn't already exist, create it...
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)

    # Return path...
    return config_dir

# Get the application version...
def get_version():
    return __version__.version

# Guess the currently logged in user's display name...
def guess_user_display_name():

    # Get login name...
    username = getpass.getuser()

    # Get the password database entry for the user...
    passwd = pwd.getpwnam(username)

    # Get the display name...
    display_name = passwd.pw_gecos.split(',')[0]

    # Return it...
    return display_name

# Are we running in a virtual environment?
def is_venv():
    return sys.prefix != sys.base_prefix

