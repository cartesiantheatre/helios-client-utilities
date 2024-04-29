#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2024 Cartesian Theatre. All rights reserved.
#

# System imports...
import platform
import subprocess

# Gtk imports...
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GdkPixbuf

# i18n...
import gettext
_ = gettext.gettext

# Take the binary image array and convert it into a GdkPixbuf.Pixbuf...
def image_data_to_pixbuf(data: bytes):

    # Construct an image loader...
    loader = GdkPixbuf.PixbufLoader.new()

    # Feed the compressed binary data into the image loader...
    loader.write(data)
    loader.close()

    # Retrieve the GdkPixBuf.Pixbuf...
    pixbuf = GdkPixbuf.PixbufLoader.get_pixbuf(loader)

    # Return it to the caller...
    return pixbuf

# Open a file or URL as though the user had launched it themselves using their 
#  preferred application...
def launch_uri(uri):

    # TODO: Replace below with Gtk.UriLauncher as soon as available.
    #launcher = Gtk.UriLauncher.new(uri)
    #launcher.launch()

    # Winblows...
    if platform.system().lower().find("win") == 0:
        os.startfile(uri)

    # OS X...
    elif platform.system().lower().find("darwin") == 0: 
        subprocess.Popen(["open", format(uri)])
    elif platform.system().lower().find("macosx") == 0: 
        subprocess.Popen(["open", format(uri)])

    # Some other OS...
    else:

        # Try freedesktop approach common on most GNU machines...
        try:
            subprocess.Popen(["xdg-open", format(uri)])
        except OSError:
            print(_("Cannot launch {0}. Platform unknown...").format(uri))

