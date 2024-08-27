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

# Helios imports...
import helios
from helios_client_utilities.trainer import *

# i18n...
import gettext
_ = gettext.gettext


# Trainer application class...
class TrainerApplication(Gtk.Application):

    # Constructor...
    def __init__(self, **kwargs):

        # Initialize base class...
        super().__init__(**kwargs)

        # Main application window will be stored here after it is created...
        self._application_window = None

        # Store training session here...
        self._training_session = TrainingSession()

        # Command line dictionary location to be populated during
        #  do_command_line() callback...
        self._command_line_dictionary = {}

        # Show help summary...
        self.set_option_context_summary(
            _('Interactive GUI for music experts to tune Helios similarity algorithms.'))

        # Add --api-key command line interface...
        self.add_main_option(
            'api-key',
            ord('a'),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.STRING,
            _('API key to submit to remote server. May or may not be required.'),
            None)

        # Add --collector-host command line interface...
        self.add_main_option(
            'collector-host',
            0,
            GLib.OptionFlags.NONE,
            GLib.OptionArg.STRING,
            _('Trainer Collector Server host to use. Defaults to trainer-collector.heliosmusic.io.'),
            None)

        # Add --collector-port command line interface...
        self.add_main_option(
            'collector-port',
            0,
            GLib.OptionFlags.NONE,
            GLib.OptionArg.INT,
            _('Trainer Collector Server port to use. Defaults to 22576.'),
            None)

        # Add --debug hidden command line interface...
        self.add_main_option(
            'debug',
            0,
            GLib.OptionFlags.HIDDEN,
            GLib.OptionArg.NONE,
            _('Enable debugging mode. Defaults to off.'),
            None)

        # Add --host command line interface...
        self.add_main_option(
            'host',
            ord('h'),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.STRING,
            _('IP address or host name of remote server. Defaults to auto.'),
            None)

        # Add --port command line interface...
        self.add_main_option(
            'port',
            ord('p'),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.INT,
            _('Port remote server is listening on. Defaults to 6440.'),
            None)

        # Add --tls-disabled command line interface...
        self.add_main_option(
            'tls-disabled',
            0,
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            _('Disable encryption. By default encryption is enabled.'),
            None)

        # Add --total-matches command line interface...
        self.add_main_option(
            'total-matches',
            ord('t'),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.INT,
            _('Total number of matches to retrieve for each search key. Defaults to 8.'),
            None)

        # Add --version command line interface...
        self.add_main_option(
            'version',
            ord('v'),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            _('Show application version information'),
            None)

        # Set path to icon theme search path if running in a virtual
        #  environment. This ensures icons still load outside of a proper Debian
        #  package...
        set_icon_theme_search()

        # Connect signals...
      #  self.connect('command-line', self.on_command_line)
        self.connect('startup', self.on_startup)
        self.connect('activate', self.on_activate)
        self.connect('shutdown', self.on_shutdown)

    # Create an action with the given callback and register with application...
    def create_action(self, name, callback):

        # Construct a new action with the given name...
        action = Gio.SimpleAction.new(name, None)

        # Connect it with the callback...
        action.connect('activate', callback)

        # Register the action with our application...
        self.add_action(action)

    # Action handler for about...
    def on_about(self, action, param):

        # Construct about dialog...
        dialog = Gtk.AboutDialog(transient_for=self.get_active_window()) 

        # Set program name...
        dialog.set_program_name(get_application_name())

        # Set program version...
        dialog.set_version(F"{helios.__version__.version}") 

        # Set license to GPL v3...
        dialog.set_license_type(Gtk.License(Gtk.License.GPL_3_0)) 

        # Set comments...
        dialog.set_comments(_("Interactive GUI for music experts to tune\n"
                              "Helios similarity algorithms."))

        # Set product website...
        dialog.set_website_label(_("Website"))
        dialog.set_website("https://www.heliosmusic.io") 

        # Set copyright year...
        dialog.set_copyright("© 2015-2024 Cartesian Theatre Corp.") 

        # Set author...
        dialog.set_authors(["Kip Warner"])

        # Add music experts...
        dialog.add_credit_section(
            "Music Experts",
            [
                "Angus Lau",
                "Joseph Liau",
                "Nathan Barrett",
                "Stephen Wright"
            ])

        # Set icon...
        dialog.set_logo_icon_name(get_application_id())

        # Display about window
        dialog.present()

    # Signal handler for application activation...
    def on_activate(self, application):

        # Launch the main window, but only if it doesn't already exist...
        if not self._application_window:
            self._application_window = ApplicationWindow(application=application)

        # Make main window visible...
        self._application_window.present()

    # Parse command line...
    def do_command_line(self, command_line):

        # Get command line options and convert from GVariantDict to GVariant and
        #  in turn into a normal Python dictionary...
        options = command_line.get_options_dict()
        self._command_line_dictionary = options.end().unpack()

        # User requested version...
        if 'version' in self._command_line_dictionary:

            # Dump it...
            print(F'helios-trainer {get_version()}')

            # Don't activate application. Exit instead...
            return 0

        # Continue with application invocation...
        self.activate()

        # Return an integer that is set as the exit status...
        return 0

    # Return command line dictionary...
    def get_command_line_dictionary(self):
        return self._command_line_dictionary

    # Action handler for quit...
    def on_quit(self, action, param):

        # Exit...
        self.quit()

    # Open issue tracker...
    def on_report_issue(self, action, param):
        launch_uri('https://github.com/cartesiantheatre/helios-client-utilities/issues')

    # Application shutting down...
    def on_shutdown(self, application):

        # If the GUI was loaded...
        if self._application_window is not None:

            # Then cleanup any cached matches in the queue, while there are
            #  some...
            while self._application_window._asset_loader_page._match_bundle_queue.qsize():

                # Retrieve a match bundle...
                match_bundle = self._application_window._asset_loader_page._match_bundle_queue.get()

                # Notify queue the enqueued task is complete...
                self._application_window._asset_loader_page._match_bundle_queue.task_done()

                # Clean it up...
                match_bundle.cleanup()

            # Cleanup the current match bundle, if any...
            self._application_window._match_tuner_page.reset()

    # Signal handler for application startup. This signal is emitted on the
    #  primary instance immediately after registration...
    def on_startup(self, user_data):

        # Create basic actions...
        self.create_action('about', self.on_about)
        self.create_action('quit', self.on_quit)
        self.create_action('report_issue', self.on_report_issue)
        self.create_action('website', self.on_website)

        # Dark mode action...
        #action = Gio.SimpleAction.new_stateful('dark_mode', None, GLib.Variant('b', False))
        #action.connect('change-state', self.on_dark_mode)
        #self.add_action(action)

        # Comment out to start in system theme instead of dark mode...
        #action.change_state(GLib.Variant.new_boolean(True))

    # Open product website...
    def on_website(self, action, param):
        launch_uri('https://www.heliosmusic.io')

