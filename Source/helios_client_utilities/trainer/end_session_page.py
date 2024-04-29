#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2024 Cartesian Theatre. All rights reserved.
#

# System imports...
import os
import re
import threading
import time

# urllib3...
import urllib3

# Gtk related imports...
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gio, Gtk, GLib

# Helios...
from helios_client_utilities.trainer import *

# Requests...
import requests
from requests.adapters import HTTPAdapter, Retry
from requests_toolbelt.utils import user_agent as ua

# i18n...
import gettext
_ = gettext.gettext

# End session page class...
class EndSessionPage(StackPage):

    # Constructor...
    def __init__(self, application_window):

        # Initialize base class...
        super().__init__(application_window, name='EndSession', title=_('End Session'))

        # Store reference to application window...
        self._application_window = application_window

        # Create master sizer...
        self._sizer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._sizer.set_margin_top(20)
        self._sizer.set_margin_start(20)
        self._sizer.set_margin_bottom(20)
        self._sizer.set_margin_end(20)

        # Create instructions label...
        self._instructions_label = Gtk.Label.new()
        self._instructions_label.set_use_markup(True)
        self._instructions_label.set_wrap(True)
        self._instructions_label.set_halign(Gtk.Align.FILL)
        self._instructions_label.set_hexpand(True)
        self._instructions_label.set_vexpand(True)
        #self._instructions_label.set_markup(_(F'Thank you for providing {self._application._training_session.get_total_examples()} data points to help improve the performance of Helios! You can now submit your training session data noted below to the Helios servers\' system administrator automatically, if you wish:\n\n{self._application._training_session.get_path()}'))
        self._sizer.append(self._instructions_label)

        # Construct rights check button...
        self._consent_checkbutton = Gtk.CheckButton()
        self._consent_checkbutton.set_active(False)
        self._consent_checkbutton.set_halign(Gtk.Align.END)
        self._consent_checkbutton.connect('toggled', self.on_consent_toggled)

        # Construct rights label...
        consent_label = Gtk.Label(label=_("I consent to assigning all of my rights over the\nabove training session data to the recipient."))
        consent_label.set_wrap(True)
        consent_label.set_size_request(100, -1)
        consent_label.set_margin_top(20)
        consent_label.set_margin_start(20)
        consent_label.set_margin_bottom(20)
        consent_label.set_margin_end(20)

        # Create consent sizer...
        consent_sizer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        consent_sizer.set_halign(Gtk.Align.CENTER)
        consent_sizer.set_margin_top(20)
        consent_sizer.set_margin_start(20)
        consent_sizer.set_margin_bottom(20)
        consent_sizer.set_margin_end(20)
        consent_sizer.append(self._consent_checkbutton)
        consent_sizer.append(consent_label)

        # Add consent sizer to master sizer...
        self._sizer.append(consent_sizer)

        # Create buttons' sizer...
        buttons_sizer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        buttons_sizer.set_halign(Gtk.Align.CENTER)
        buttons_sizer.set_margin_top(20)
        buttons_sizer.set_margin_start(20)
        buttons_sizer.set_margin_bottom(20)
        buttons_sizer.set_margin_end(20)
        self._sizer.append(buttons_sizer)

        # Create submit button...
        self._submit_button = Gtk.Button()
        submit_button_sizer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        submit_button_sizer.set_halign(Gtk.Align.CENTER)
        self._submit_button.set_size_request(150, 80)
        self._submit_button.set_child(submit_button_sizer)
        self._submit_button.set_sensitive(False)
        self._submit_button.connect('clicked', self.on_submit)
        submit_button_image = Gtk.Image.new_from_icon_name('document-send')
        submit_button_image.set_icon_size(Gtk.IconSize.LARGE)
        submit_button_label = Gtk.Label(label=_('Submit'))
        submit_button_sizer.append(submit_button_image)
        submit_button_sizer.append(submit_button_label)
        buttons_sizer.append(self._submit_button)

        # Create exit button...
        self._exit_button = Gtk.Button()
        exit_button_sizer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        exit_button_sizer.set_halign(Gtk.Align.CENTER)
        self._exit_button.set_size_request(150, 80)
        self._exit_button.set_child(exit_button_sizer)
        self._exit_button.connect('clicked', self.on_exit)
        exit_button_image = Gtk.Image.new_from_icon_name('window-close')
        exit_button_image.set_icon_size(Gtk.IconSize.LARGE)
        exit_button_label = Gtk.Label(label=_('Exit'))
        exit_button_sizer.append(exit_button_image)
        exit_button_sizer.append(exit_button_label)
        buttons_sizer.append(self._exit_button)

    # Consent checkbox toggled...
    def on_consent_toggled(self, consent_button):

        # Get consent flag...
        consent = consent_button.get_active()

        # Enable or disable submission button accordingly...
        self._submit_button.set_sensitive(consent)

    # Submit the user's training session...
    def upload_training_session(self, search_key_reference: str=None):

        # Save training session file...
        self._application._training_session.save()

        # Spawn fetch assets thread...
        self._upload_training_session_thread = threading.Thread(target=self.upload_training_session_thread_entry)
        self._upload_training_session_thread.start()

    # Entry point for user training session upload thread...
    def upload_training_session_thread_entry(self):

        # Trainer Collector daemon host and port...
        collector_server    = 'trainer-collector.heliosmusic.io'
        collector_port      = 22576

        # If user specified a collector server, use it...
        if 'collector-host' in self._application._command_line_dictionary:
            collector_server = self._application._command_line_dictionary['collector-host']

        # If user specified a collector port, use it...
        if 'collector-port' in self._application._command_line_dictionary:
            collector_port = self._application._command_line_dictionary['collector-port']

        # Trainer Collector POST submission endpoint...
        collector_endpoint  = '/training-session'

        # Try to do everything that you need to do...
        try:

            # Disable consent, submit, and exit buttons...
            GLib.idle_add(self._consent_checkbutton.set_sensitive, False)
            GLib.idle_add(self._submit_button.set_sensitive, False)
            GLib.idle_add(self._exit_button.set_sensitive, False)

            # Construct requests session...
            session = requests.Session()

            # Prepare a Retry object that will tell our HTTP adapter to retry a
            #  total number of three times and wait one second in between...
            retries = Retry(total=5, backoff_factor=1.0)

            # Construct an adaptor to automatically make three retry attempts on
            #  failed DNS lookups and connection timeouts...
            adapter = HTTPAdapter(max_retries=3)
            session.mount('http://', adapter)
            session.mount('https://', adapter)

            # Construct user agent string...
            user_agent = ua.UserAgentBuilder(
                name=get_application_name(),
                version=get_version())
            user_agent.include_system()

            # Prepare headers...
            headers = {
                'User-Agent': user_agent.build()
            }

            # Construct full URL to endpoint...
            url = F'https://{collector_server}:{collector_port}/training-session'

            # Whenever we use the parameter 'files' with requests it will
            #  set the Content-Encoding type to multipart/form-data for us. We
            #  should never manually set the Content-Encoding when using this
            #  type because then the requests library will not set the boundary
            #  field correctly...
            files = {
                'training_session': (
                    'training_session.hts',
                    open(self._application._training_session.get_path(), 'rb'),
                'application/x-helios-training-session',
                {'Expires': '0'})
            }

            # Get training session alias...
            training_session = self._application._training_session

            # Prepare form values...
            values = {
                'expert_name' : training_session.get_expert_name(),
                'expert_email' : training_session.get_expert_email(),
                'helios_server_host' : training_session.get_host(),
                'helios_server_port' : training_session.get_port(),
                'helios_server_tls' : training_session.get_tls(),
                'helios_server_version' : training_session.get_version(),
                'helios_api_key' : training_session.get_api_key()
            }

            # Inform user of what we're doing...
            GLib.idle_add(self._application_window.set_status, _(F'Connecting to {collector_server}:{collector_port}, please wait...'))

            # Disable server certificate verification...
            urllib3.disable_warnings()

            # Try uploading to Trainer Collector server...
            response = session.post(url, headers=headers, files=files, data=values, verify=False)

            # We reached the server. If we didn't get an expected response,
            #  raise an exception...
            response.raise_for_status()

            # Set the server's response in the instruction label...
            GLib.idle_add(self._instructions_label.set_markup, response.text)

            # Inform user of what we're doing...
            GLib.idle_add(self._application_window.set_status, _('Done!'))

        # Something went wrong...
        except Exception as some_exception:

            # Create an alert dialog...
            alert_dialog = Gtk.AlertDialog()
            alert_dialog.set_message(_('Error'))
            alert_dialog.set_detail(_(F'A problem occurred while submitting your training session data. Would you like me to try again?\n\n{str(some_exception)}'))
            alert_dialog.set_buttons([_('Exit'), _('Retry')])
            alert_dialog.set_default_button(1)
            alert_dialog.set_modal(True)

            # Show it...
            GLib.idle_add(alert_dialog.choose, self._application_window, None, self.on_alert_dialog_callback, None)

            # Enable submit button to allow retry...
            GLib.idle_add(self._submit_button.set_sensitive, True)

        # Regardless of what happens...
        finally:

            # Re-enable consent and exit button...
            GLib.idle_add(self._consent_checkbutton.set_sensitive, False)
            GLib.idle_add(self._exit_button.set_sensitive, True)

    # Callback for alert dialog...
    def on_alert_dialog_callback(self, alert_dialog, async_result, _):

        # Get the user's selection...
        selection = alert_dialog.choose_finish(async_result)

        # User requested to exit...
        if selection == 0:

            # Quit...
            self._application.quit()

        # Otherwise user requested to retry, so do it...
        else:
            self.upload_training_session()

    # Submit button clicked...
    def on_submit(self, button):

        # Spawn upload training session thread...
        self.upload_training_session()

    # Exit button clicked...
    def on_exit(self, button):

        # Quit application...
        self._application.quit()

