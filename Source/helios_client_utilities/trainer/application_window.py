#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2024 Cartesian Theatre. All rights reserved.
#

# System imports...
import os

# Gtk related imports...
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gio, Gtk, GLib

# Helios...
from helios_client_utilities.trainer import *

# i18n...
import gettext
_ = gettext.gettext

# Main application window class...
class ApplicationWindow(Gtk.ApplicationWindow):

    # Constructor...
    def __init__(self, *args, **kwargs):

        # Initialize base class...
        super().__init__(*args, **kwargs)

        # Get the application...
        self._application = self.get_application()

        # Set the default size...
        self.set_default_size(1200, 800)

        # Set window title...
        self.set_title(get_application_name())

        # Connect signals and property watches for window itself...
        self.connect('notify::fullscreened', self.on_notify_fullscreened)

        # Create a top level box container and set as the sole child of
        #  window...
        self._master_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_child(self._master_vbox)

        # Construct GtkBuilder for parsing menu XML definition and retrieve menu
        #  model...
        builder = Gtk.Builder.new_from_string(menu_xml, -1)
        menumodel = builder.get_object("ApplicationMenu")

        # Construct popover menu bar from menu model...
        self._menubar = Gtk.PopoverMenuBar.new_from_model(menumodel)

        # Create a status area horizontal box...
        status_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        status_hbox.set_margin_top(2)
        status_hbox.set_margin_start(10)
        status_hbox.set_margin_bottom(5)
        status_hbox.set_margin_end(5)

        # Create a status label...
        self._status_label = Gtk.Label(label=_('Status area...'))
        self._status_label.set_hexpand(True)
        self._status_label.set_halign(Gtk.Align.START)
        self._status_label.set_valign(Gtk.Align.END)

        # Create a status progress bar...
        self._status_progress = Gtk.ProgressBar()
        self._status_progress.set_size_request(400, 10)
        self._status_progress.set_vexpand(True)
        self._status_progress.set_valign(Gtk.Align.END)
        self.set_progress_visible(False)

        # Add status label and progress bar to status area layout box...
        status_hbox.append(self._status_label)
        status_hbox.append(self._status_progress)

        # Create a stack which will contain all of the different pages...
        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._stack.set_transition_duration(250)

        # Create and add the login page...
        self._login_page = LoginPage(application_window=self)
        self._login_page.add_to_stack(self._stack)

        # Create and add the quick start page...
        self._quick_start_page = QuickStartPage(application_window=self)
        self._quick_start_page.add_to_stack(self._stack)

        # Create and add the session selector page...
        self._session_selector_page = SessionSelectorPage(application_window=self)
        self._session_selector_page.add_to_stack(self._stack)

        # Create and add the asset loader page...
        self._asset_loader_page = AssetLoaderPage(application_window=self)
        self._asset_loader_page.add_to_stack(self._stack)

        # Create and add the match tuner page...
        self._match_tuner_page = MatchTunerPage(application_window=self)
        self._match_tuner_page.add_to_stack(self._stack)

        # Create and add the end session page...
        self._end_session_page = EndSessionPage(application_window=self)
        self._end_session_page.add_to_stack(self._stack)

        # Create a stack switcher to be used during debugging to reveal all
        #  pages...
        stack_switcher = Gtk.StackSwitcher()
        stack_switcher.set_stack(self._stack)
        stack_switcher.set_visible(False)

        # If user enabled debug mode...
        if 'debug' in self._application._command_line_dictionary:

            # Make stack switcher visible...
            stack_switcher.set_visible(True)

        # Add menu bar, stack switcher, stack, and status area to top level box
        #  container...
        self._master_vbox.append(self._menubar)
        self._master_vbox.append(stack_switcher)
        self._master_vbox.append(self._stack)
        self._master_vbox.append(status_hbox)

        # Register all actions...
        self.connect_actions()

        # Set status to welcome message and hide progress bar...
        self.set_status(_('Welcome!'))

        # Upon successful login, this will contain the client...
        self._client = None

    # Register all actions for window...
    def connect_actions(self):

        # End session action, but start with it disabled...
        self._end_session_action = self.create_action('end_session', self.on_end_session)
        self._end_session_action.set_enabled(False)

        # Fullscreen action...
        action = Gio.SimpleAction.new_stateful('fullscreen', None, GLib.Variant('b', False))
        action.connect('change-state', self.on_fullscreen)
        self.add_action(action)

    # Create an action with the given callback and register with window...
    def create_action(self, name, callback):

        # Construct a new action with the given name...
        action = Gio.SimpleAction.new(name, None)

        # Connect it with the callback...
        action.connect('activate', callback)

        # Register the action with our application...
        self.add_action(action)

        # Return the action to caller, in case it needs it...
        return action

    # Action for ending a session...
    def on_end_session(self, action, parameter):

        # Switch to end session page...
        self._stack.set_visible_child_name('EndSession')

        # Set status bar...
        self.set_status(_('Ready to submit your training session data...'))

        # Update the instructions label on the end session page...
        self._end_session_page._instructions_label.set_markup(_(F'Thank you for providing {self._application._training_session.get_total_examples()} data points to help improve the performance of Helios! You can now submit your training session data noted below to the Helios servers\' system administrator automatically, if you wish:\n\n{self._application._training_session.get_path()}'))

    # Action for toggling fullscreen...
    def on_fullscreen(self, action, parameter):

        # Fullscreen is currently enabled. Disable it...
        if self.is_fullscreen():
            self.unfullscreen()

        # Otherwise enable it...
        else:
            self.fullscreen()

    # State of the toplevel window associated with the given widget has
    #  changed...
    def on_notify_fullscreened(self, gobject, parameter):

        # Get whether fullscreen is toggled or not...
        is_fullscreen = self.get_property(parameter.name)

        # Toggle menu item...
        menuitem = self.lookup_action('fullscreen')
        menuitem.set_state(GLib.Variant('b', is_fullscreen))

    # Set status text...
    def set_status(self, message):
        self._status_label.set_label(message)

    # Update progress bar. Fraction should be in [0, 1] range...
    def set_progress(self, fraction: float):
        self._status_progress.set_fraction(fraction)
        #print(F'fraction = {fraction}')

    # Toggle progress bar visibility...
    def set_progress_visible(self, visible):
        self._status_progress.set_visible(visible)

