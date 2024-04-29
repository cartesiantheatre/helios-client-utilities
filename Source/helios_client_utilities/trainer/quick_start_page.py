#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2024 Cartesian Theatre. All rights reserved.
#

# System imports...
import os
import re
import threading

# Gtk related imports...
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gio, Gtk, GLib

# Helios...
from helios_client_utilities.trainer import *

# i18n...
import gettext
_ = gettext.gettext

# Quick start page class...
class QuickStartPage(StackPage):

    # Constructor...
    def __init__(self, application_window):

        # Initialize base class...
        super().__init__(application_window, name='QuickStart', title=_('Quick Start'))

        # Store reference to application window...
        self._application_window = application_window

        # Construct master sizer...
        self._sizer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._sizer.set_margin_top(20)
        self._sizer.set_margin_start(20)
        self._sizer.set_margin_bottom(20)
        self._sizer.set_margin_end(20)

        # Construct label for guide...
        guide_label = Gtk.Label.new()
        guide_label.set_use_markup(True)
        guide_label.set_wrap(True)
        guide_label.set_halign(Gtk.Align.FILL)
        guide_label.set_hexpand(True)
        guide_label.set_vexpand(True)
        guide_text = self.get_quick_start_text()
        guide_label.set_markup(guide_text)

        # Put text view guide within a scrolled window...
        scrolled_window = Gtk.ScrolledWindow.new()
        scrolled_window.set_child(guide_label)
        scrolled_window.connect('edge-reached', self.on_scroll_edge_reached)

        # Create ready button...
        self._got_it_button = Gtk.Button()
        self._got_it_button.set_halign(Gtk.Align.END)
        got_it_button_sizer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._got_it_button.set_child(got_it_button_sizer)
        self._got_it_button.set_sensitive(False)
        self._got_it_button.connect('clicked', self.on_got_it)
        got_it_button_image = Gtk.Image.new_from_icon_name('go-next')
        got_it_button_image.set_icon_size(Gtk.IconSize.LARGE)
        got_it_button_label = Gtk.Label(label=_('Got it!'))
        got_it_button_sizer.append(got_it_button_image)
        got_it_button_sizer.append(got_it_button_label)

        # Add widgets to master sizer...
        self._sizer.append(scrolled_window)
        self._sizer.append(self._got_it_button)

    # Load quick start text from disk...
    def get_quick_start_text(self):

        # Get path to text file...
        text_file_path = os.path.join(get_data_dir(), 'text/quick_start_page.txt')

        # Load and return it...
        with open(text_file_path) as file:
            return file.read()

    # Got it button clicked...
    def on_got_it(self, button):

        # Switch to session selector page...
        self._application_window._stack.set_visible_child_name('SessionSelector')

        # Set status message...
        self._application_window.set_status(_('Please configure your training session...'))

    # Scrollbar reached a limit...
    def on_scroll_edge_reached(self, scrolled_window, position):

        # If the user scrolled to the bottom of the guide then enable button...
        if position is Gtk.PositionType.BOTTOM:
            self._got_it_button.set_sensitive(True)

