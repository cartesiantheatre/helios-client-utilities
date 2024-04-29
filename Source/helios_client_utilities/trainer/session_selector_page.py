#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2024 Cartesian Theatre. All rights reserved.
#

# System imports...
import getpass
import os
import pathlib
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

# Session selector page class...
class SessionSelectorPage(StackPage):

    # Constructor...
    def __init__(self, application_window):

        # Initialize base class...
        super().__init__(application_window, name='SessionSelector', title=_('Session Selector'))

        # Store reference to application window...
        self._application_window = application_window

        # Construct master sizer...
        self._sizer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self._sizer.set_vexpand(True)
        self._sizer.set_valign(Gtk.Align.CENTER)
        self._sizer.set_margin_top(20)
        self._sizer.set_margin_start(20)
        self._sizer.set_margin_bottom(20)
        self._sizer.set_margin_end(20)

        # Construct name label...
        name_label = Gtk.Label(label=_("Your name:"))
        name_label.set_halign(Gtk.Align.END)

        # Construct name entry...
        self._name_entry = Gtk.Entry()
        self._name_entry.set_input_purpose(Gtk.InputPurpose.NAME)
        self._name_entry.set_size_request(300, 20)
        self._name_entry.set_alignment(0.5)
        self._name_entry.set_text(guess_user_display_name())
        self._name_entry.connect('notify::text', self.on_name_or_email_text_change)

        # Construct email label...
        email_label = Gtk.Label(label=_("Your email:"))
        email_label.set_halign(Gtk.Align.END)

        # Construct email entry...
        self._email_entry = Gtk.Entry()
        self._email_entry.set_input_purpose(Gtk.InputPurpose.EMAIL)
        #self._email_entry.set_placeholder_text(_('your@email.com'))
        self._email_entry.set_alignment(0.5)
        self._email_entry.connect('notify::text', self.on_name_or_email_text_change)

        # Construct grid for expert fields...
        expert_grid = Gtk.Grid()
        expert_grid.set_vexpand(True)
        expert_grid.set_valign(Gtk.Align.CENTER)
        expert_grid.set_halign(Gtk.Align.CENTER)
        expert_grid.set_row_spacing(20)
        expert_grid.set_column_spacing(20)

        # Populate the expert grid... left, top, width, height
        expert_grid.attach(name_label, 0, 0, 1, 1)
        expert_grid.attach(self._name_entry, 1, 0, 1, 1)
        expert_grid.attach(email_label, 0, 1, 1, 1)
        expert_grid.attach(self._email_entry, 1, 1, 1, 1)

        # Create a frame around the name and email address...
        #expert_frame = Gtk.Frame()
        #expert_frame.set_label(_('Expert information:'))
        #expert_frame.set_child(expert_grid)
        self._sizer.append(expert_grid)

        # Create start new session radio button...
        self._new_session = Gtk.CheckButton.new_with_label(_('Start new training session file'))
        self._new_session.set_halign(Gtk.Align.START)
        self._new_session.set_active(True)
        self._new_session.connect('toggled', self.on_session_radio_select)

        # Create a resume session radio button...
        self._resume_session = Gtk.CheckButton.new_with_label(_('Resume previous training session file'))
        self._resume_session.set_halign(Gtk.Align.START)
        self._resume_session.connect('toggled', self.on_session_radio_select)
        self._resume_session.set_group(self._new_session)

        # Location to store training session file...
        self._file_path = None

        # Construct sizer for session type check buttons...
        session_type_sizer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        session_type_sizer.set_vexpand(True)
        session_type_sizer.set_halign(Gtk.Align.CENTER)
        session_type_sizer.set_margin_top(20)
        session_type_sizer.set_margin_start(20)
        session_type_sizer.set_margin_bottom(20)
        session_type_sizer.set_margin_end(20)
        session_type_sizer.append(self._new_session)
        session_type_sizer.append(self._resume_session)
        self._sizer.append(session_type_sizer)

        # Create sizer for location and ready buttons...
        button_sizer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        button_sizer.set_vexpand(True)
        button_sizer.set_halign(Gtk.Align.CENTER)
        button_sizer.set_margin_top(20)
        button_sizer.set_margin_start(20)
        button_sizer.set_margin_bottom(20)
        button_sizer.set_margin_end(20)

        # Create a file chooser button...
        self._select_session_button = Gtk.Button()
        select_session_button_sizer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        select_session_button_sizer.set_halign(Gtk.Align.CENTER)
        self._select_session_button.set_child(select_session_button_sizer)
        self._select_session_button.connect('clicked', self.on_select_session)
        select_session_button_image = Gtk.Image.new_from_icon_name('folder')
        select_session_button_image.set_icon_size(Gtk.IconSize.LARGE)
        self._select_session_button_label = Gtk.Label()
        select_session_button_sizer.append(select_session_button_image)
        select_session_button_sizer.append(self._select_session_button_label)
        button_sizer.append(self._select_session_button)

        # Create ready button...
        self._ready_button = Gtk.Button()
        ready_button_sizer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        ready_button_sizer.set_halign(Gtk.Align.CENTER)
        self._ready_button.set_child(ready_button_sizer)
        self._ready_button.set_sensitive(False)
        self._ready_button.connect('clicked', self.on_ready)
        ready_button_image = Gtk.Image.new_from_icon_name('go-next')
        ready_button_image.set_icon_size(Gtk.IconSize.LARGE)
        self._ready_button_label = Gtk.Label(label=_('Ready'))
        ready_button_sizer.append(ready_button_image)
        ready_button_sizer.append(self._ready_button_label)
        button_sizer.append(self._ready_button)

        # Add button sizer to master sizer...
        self._sizer.append(button_sizer)

        # Update UI based on starting a new training session...
        self._new_session.emit('toggled')

    # Guess the best default location to save a session...
    def default_save_file(self):

        # Get home directory...
        home = pathlib.Path.home()

        # Get login name...
        username = getpass.getuser()

        # Get path to desktop directory...
        desktop_path = os.path.join(home, 'Desktop')

        # If there is a desktop folder, then default to saving session there...
        if os.path.exists(desktop_path):
            return os.path.join(desktop_path, username + '.hts')

        # Otherwise default to home directory...
        else:
            return os.path.join(home, username + '.hts')

    # Either the name or email text changed...
    def on_name_or_email_text_change(self, entry_buffer, result):

        # Update submission ready state...
        self.update_ready_state()

    # Ready button clicked...
    def on_ready(self, button):

        # Try to create new or resume previous session...
        try:

            # If user requested to restore a previous session, start by loading
            #  it before overwriting expert and server related details with
            #  whatever is current...
            if not self._new_session.get_active():
                self._application._training_session.load(self._file_path)

            # Get the login page...
            login_page = self._application_window._login_page

            # Set API key...
            api_key = login_page._api_key_entry.get_text()
            self._application._training_session.set_api_key(api_key)

            # Set host...
            host = login_page._host_entry.get_text()
            self._application._training_session.set_host(host)

            # Set port...
            port = int(login_page._port_entry.get_text())
            self._application._training_session.set_port(port)

            # Set TLS flag...
            tls = login_page._use_tls_switch.get_active()
            self._application._training_session.set_tls(tls)

            # Set expert name...
            expert_name = self._name_entry.get_text()
            self._application._training_session.set_expert_name(expert_name)

            # Set expert email...
            expert_email = self._email_entry.get_text()
            self._application._training_session.set_expert_email(expert_email)

            # Set server version...
            server_version = self._application._system_status.version
            self._application._training_session.set_version(server_version)

            # Save session to disk...
            self._application._training_session.save(self._file_path)

        # Something bad happened...
        except Exception as some_exception:

            # Show error message in status bar...
            self._application_window.set_status(str(some_exception))

            # Disable ready button...
            self._ready_button.set_sensitive(False)

            # Don't do anything else...
            return

        # Switch to asset loader page if everything went find...
        self._application_window._stack.set_visible_child_name('AssetLoader')

        # Start fetching the next set of assets...
        self._application_window._asset_loader_page.fetch_assets()

    # Select session file button clicked...
    def on_select_session(self, button):

        # File filter to open .hts files...
        file_filter = Gtk.FileFilter()
        file_filter.set_name(_('Helios training sessions (.hts)'))
        file_filter.add_mime_type('application/x-helios-training-session')
        file_filter.add_suffix('hts')

        # All other files filter...
        all_files_filter = Gtk.FileFilter()
        all_files_filter.set_name(_('All files'))
        all_files_filter.add_pattern('*')

        # Create list of filters for dialog...
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(file_filter)
        filters.append(all_files_filter)

        # Construct file dialog...
        file_dialog = Gtk.FileDialog.new()
        file_dialog.set_filters(filters)
        file_dialog.set_default_filter(file_filter)
        file_dialog.set_initial_file(Gio.File.new_for_path(self.default_save_file()))

        # Creating a new session...
        if self._new_session.get_active():

            # Construct file dialog...
            file_dialog.set_title(_('Select location to save training session'))

            # Show dialog...
            file_dialog.save(self._application_window, None, self.on_file_dialog_open)

        # Restoring a previous one...
        else:

            # Construct file dialog...
            file_dialog.set_title(_('Select training session to resume'))

            # Show dialog...
            file_dialog.open(self._application_window, None, self.on_file_dialog_open)

    # The user has selected a session file from the file dialog...
    def on_file_dialog_open(self, file_dialog, result):

        # Creating a new session...
        if self._new_session.get_active():

            # Try to get path...
            try:
                file_object = file_dialog.save_finish(result)

            # Or do nothing if user cancels...
            except:
                return

            # Get path to file...
            self._file_path = file_object.get_path()

            # Seperate the base name from the extension...
            file_name, file_extension = os.path.splitext(self._file_path)

            # If extension isn't there, add it...
            if file_extension.lower() != '.hts':
                self._file_path = file_name + '.hts'

        # Restoring a previous one...
        else:

            # Try to get path...
            try:
                file_object = file_dialog.open_finish(result)

            # Or do nothing if user cancels...
            except:
                return

            # Get path to file...
            self._file_path = file_object.get_path()

            # If the path can't be accessed...
            if not os.path.isfile(self._file_path) or not os.access(self._file_path, os.R_OK):

                # Create an alert dialog...
                alert_dialog = Gtk.AlertDialog.new(_(F'The training session you selected cannot be read:\n{self._file_path}'))
                alert_dialog.set_buttons([_(F'Ok')])
                alert_dialog.set_modal(True)
                alert_dialog.show(self)

                # Clear the path...
                self._file_path = None
                self._application_window.set_status(_(F'Cannot read from {self._file_path}'))

                # Update ready state...
                self.update_ready_state()

                # Don't do anything else...
                return

        # Show path to file in status bar...
        self._application_window.set_status(_(F'Training session location: {self._file_path}'))

        # Update ready state...
        self.update_ready_state()

    # Session selector radio button clicked...
    def on_session_radio_select(self, radio_button):

        # New session selected...
        if self._new_session.get_active():

            # Update select session button label...
            self._select_session_button_label.set_label(_('Select location to save session'))

            # Enable name and email address...
            self._name_entry.set_sensitive(True)
            self._email_entry.set_sensitive(True)

        # Resume previous session...
        else:

            # Update select session button label...
            self._select_session_button_label.set_label(_('Select session to resume'))

            # Disable name and email address...
            self._name_entry.set_sensitive(False)
            self._email_entry.set_sensitive(False)

    # Update submission ready state in response to a change in user input...
    def update_ready_state(self):

        # Ready flag set if all user input prerequisites have been satisfied...
        ready = False

        # If a new session was selected...
        if self._new_session.get_active():

            # True if expert name provided...
            expert_name_ready = False

            # True if valid expert email address provided...
            expert_email_ready = False

            # Was user provided name...
            if len(self._name_entry.get_text()) > 0:
                expert_name_ready = True

            # Was a valid email address provided?
            if re.match(r"[^@]+@[^@]+\.[^@]+", self._email_entry.get_text()):
                expert_email_ready = True

            # We're ready only if all user input prerequisites satisfied...
            ready = expert_name_ready and expert_email_ready and self._file_path is not None and len(self._file_path)

        # Resuming a session was selected instead...
        else:

            # We're ready only if all user input prerequisites satisfied...
            ready = self._file_path is not None and len(self._file_path)

        # Toggle ready button sensitivity based on whether we're ready...
        self._ready_button.set_sensitive(ready)

