#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2024 Cartesian Theatre. All rights reserved.
#

# System imports...
import os
import re

# Gtk related imports...
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gio, Gtk, GLib, Gdk

# Helios...
import helios
from helios_client_utilities.trainer import *
from helios_client_utilities.common import zeroconf_find_server

# i18n...
import gettext
_ = gettext.gettext

# Login page class...
class LoginPage(StackPage):

    # Constructor...
    def __init__(self, application_window):

        # Initialize base class...
        super().__init__(application_window, name='Login', title=_('Login'))

        # This will contain the login thread...
        self._login_thread = None

        # This will contain the sizer the application window will use to contain
        #  all of this page's child widgets...
        self._sizer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._sizer.set_halign(Gtk.Align.CENTER)

        # Create login page artwork...
        logo_image = Gtk.Image.new_from_file(
            os.path.join(get_data_dir(), 'login_logo.png'))
        logo_image.set_size_request(400, 400)
        logo_image.set_valign(Gtk.Align.CENTER)
        logo_image.set_halign(Gtk.Align.END)
        logo_image.set_margin_top(10)
        logo_image.set_margin_start(80)
        logo_image.set_margin_bottom(10)
        logo_image.set_margin_end(80)

        # Add the login artwork to master sizer...
        self._sizer.append(logo_image)

        # Create a grid layout to contain all the login user interface...
        grid = Gtk.Grid()
        grid.set_vexpand(True)
        grid.set_valign(Gtk.Align.CENTER)
        grid.set_halign(Gtk.Align.START)
        grid.set_row_spacing(20)
        grid.set_column_spacing(20)

        # Construct API key label...
        api_key_label = Gtk.Label(label=_("API Key:"))
        api_key_label.set_halign(Gtk.Align.END)

        # Construct API key password entry...
        self._api_key_entry = Gtk.PasswordEntry()
        self._api_key_entry.set_show_peek_icon(True)
        self._api_key_entry.set_size_request(500, 20)
        self._api_key_entry.set_alignment(0.5)
        self._api_key_entry.connect('notify::text', self.on_login_text_change)
        #self._api_key_entry.connect('activate', self.on_entry_activate)

        # Construct host label...
        host_label = Gtk.Label(label=_("Host:"))
        host_label.set_halign(Gtk.Align.END)

        # Construct host entry...
        self._host_entry = Gtk.Entry()
        self._host_entry.set_alignment(0.5)
        self._host_entry.set_text('demobackend.heliosmusic.io')
        self._host_entry.get_buffer().connect('notify::text', self.on_login_text_change)
        #self._host_entry.connect('activate', self.on_entry_activate)

        # Construct port label...
        port_label = Gtk.Label(label=_("Port:"))
        port_label.set_halign(Gtk.Align.END)

        # Construct port entry...
        self._port_entry = Gtk.Entry()
        self._port_entry.set_input_purpose(Gtk.InputPurpose.DIGITS)
        self._port_entry.set_alignment(0.5)
        self._port_entry.set_text('6440')
        self._port_entry_insert_signal = self._port_entry.get_buffer().connect('inserted-text', self.on_port_text_change)
        self._port_entry.get_buffer().connect('notify::text', self.on_login_text_change)
        #self._port_entry.connect('activate', self.on_entry_activate)

        # Construct TLS label...
        use_tls_label = Gtk.Label(label=_("Use TLS:"))
        use_tls_label.set_halign(Gtk.Align.END)

        # Construct TLS switch...
        self._use_tls_switch = Gtk.Switch()
        self._use_tls_switch.set_halign(Gtk.Align.START)
        self._use_tls_switch.set_active(True)

        # Create login spinner...
        self._login_spinner = Gtk.Spinner()
        self._login_spinner.set_spinning(False)

        # Create find servers button...
        self._find_servers_button = Gtk.Button(label=_("Find Servers"))
        self._find_servers_button.connect('clicked', self.on_find_servers)

        # Create login button...
        self._login_button = Gtk.Button(label=_("Login"))
        #self._login_button.set_sensitive(False)
        self._login_button.connect('clicked', self.on_login_button)

        # Populate the login grid... left, top, width, height
        grid.attach(api_key_label, 0, 0, 1, 1)
        grid.attach(self._api_key_entry, 1, 0, 2, 1)
        grid.attach(host_label, 0, 1, 1, 1)
        grid.attach(self._host_entry, 1, 1, 2, 1)
        grid.attach(port_label, 0, 2, 1, 1)
        grid.attach(self._port_entry, 1, 2, 1, 1)
        grid.attach(use_tls_label, 0, 3, 1, 1)
        grid.attach(self._use_tls_switch, 1, 3, 1, 1)
        grid.attach(self._login_spinner, 0, 4, 1, 1)
        grid.attach(self._find_servers_button, 1, 4, 1, 1)
        grid.attach(self._login_button, 2, 4, 1, 1)

        # Add the login grid to master sizer...
        self._sizer.append(grid)

        # Get command line argument parser from main application window...
        command_line_dictionary = self._application_window.get_application().get_command_line_dictionary()

        # If API key was provided on the command line, use it...
        if 'api-key' in command_line_dictionary:
            self._api_key_entry.set_text(command_line_dictionary['api-key'])

        # If host was provided on the command line, use it...
        if 'host' in command_line_dictionary:
            self._host_entry.set_text(command_line_dictionary['host'])

        # If port was provided on the command line, use it...
        if 'port' in command_line_dictionary:
            self._port_entry.set_text(str(command_line_dictionary['port']))

        # If TLS was disabled on the command line, untoggle switch in user
        #  interface...
        if 'tls-disabled' in command_line_dictionary:
            self._use_tls_switch.set_active(not command_line_dictionary['tls-disabled'])

        # If user did not provide any connection details on command line
        #  interface, then try and guess host, port, and TLS by scanning LAN...
        if 'host' not in command_line_dictionary and 'port' not in command_line_dictionary and 'tls-disabled' not in command_line_dictionary:

            # Try probing LAN for first found server...
            try:

                # Probe for at most three seconds...
                auto_host, auto_port, auto_use_tls = zeroconf_find_server(wait_time=3.0)

                # Update user interface with first host we found...
                self._host_entry.set_text(auto_host[0])
                self._port_entry.set_text(str(auto_port))
                self._use_tls_switch.set_active(auto_use_tls)

            # If we found nothing, wait for user to enter it manually...
            except:
                pass

    # Login thread entry point...
    def login_thread_entry(self):

        # Toggle the login user interface to reflect a busy state...
        self.set_login_busy(True)

        # Get API key...
        api_key = self._api_key_entry.get_text()

        # Get host...
        host = self._host_entry.get_text()

        # Get port...
        port = int(self._port_entry.get_text())

        # Get TLS flag...
        tls = self._use_tls_switch.get_active()

        # Update status...
        GLib.idle_add(self._application_window.set_status, _(F'Connecting to {host}:{port}, please wait...'))

        # Try to query server status...
        try:

            # Create a client...
            self._application._client = helios.Client(
                host=host,
                port=port,
                api_key=api_key,
                tls=tls)

            # Perform query...
            self._application._system_status = self._application._client.get_system_status()

            # Check if enough songs...
            if self._application._system_status.songs < 1000:
                raise Exception(_(F'Server has {self._application._system_status.songs} songs, but you need at least a thousand for training to be useful...'))

            # Update status...
            GLib.idle_add(self._application_window.set_status, _(F"Successfully authenticated. Found {format(self._application._system_status.songs, ',d')} songs..."))

            # Switch to quick start page...
            GLib.idle_add(self._application_window._stack.set_visible_child_name, 'QuickStart')

        # Authorization problem...
        except helios.exceptions.Unauthorized:
            GLib.idle_add(self._application_window.set_status, _('Error: Server declined authorization request. Please try again...'))

        # Some other exception...
        except Exception as some_exception:
            GLib.idle_add(self._application_window.set_status, _(F'Error: {str(some_exception)}'))

        # Regardless of whether we login or not...
        finally:

            # Toggle the login user interface to reflect a non-busy state...
            GLib.idle_add(self.set_login_busy, False)

    # Activate signal on one of the entries. This means the Enter key has been
    #  pressed...
    def on_entry_activate(self, entry):

        # If the login button is enabled, click it...
        if self._login_button.get_sensitive():
            self._login_button.activate()

        # TODO: Figure out how to properly handle this event once done with the
        #  above. This is not correct according to a Gtk-WARNING emitted which
        #  says: "If you handle this event, you must return GDK_EVENT_PROPAGATE
        #  so the default handler gets the event as well"
        return True

    # Find servers button clicked...
    def on_find_servers(self, button):

        # Construct window...
        find_servers_window = FindServersWindow(self)

        # Show it...
        find_servers_window.present()

    # Login button clicked...
    def on_login_button(self, button):

        # Disable button until login complete...
        self._login_button.set_sensitive(False)

        # Spawn login thread...
        self._login_thread = SafeThread(target=self.login_thread_entry)
        self._login_thread.start()

    # One of the login text fields changed...
    def on_login_text_change(self, entry_buffer, result):

        # If one of the mandatory fields is empty, disable the login button...
        if not len(self._host_entry.get_text()) or not len(self._port_entry.get_text()):
            self._login_button.set_sensitive(False)

        # Otherwise enable it...
        else:
            self._login_button.set_sensitive(True)

    # Same as above, but only monitors port field...
    def on_port_text_change(self, text_buffer, text_iterator, text, length):

        # Get the text buffer used by the port field...
        port_text = self._port_entry.get_text()
        port_entry_buffer = self._port_entry.get_buffer()

        # If there are some non-numeric characters present...
        if not port_text.isnumeric():

            # Temporarily block signal emission arising from editing the port
            #  entry field...
            port_entry_buffer.handler_block(self._port_entry_insert_signal)

            # Remove the non-numeric characters...
            port_text = re.sub(r'[^0-9]', '', port_text)

            # Set the sanitized string back into the widget...
            port_entry_buffer.set_text(port_text, len(port_text))

            # Restore signal emission...
            port_entry_buffer.handler_unblock(self._port_entry_insert_signal)

            # But don't propagate the current signal that invoked us now...
            port_entry_buffer.emit_stop_by_name('inserted-text')

    # Toggle the login user interface to reflect a busy / non-busy state...
    def set_login_busy(self, busy):

        # Toggle widget sensitivity...
        self._api_key_entry.set_sensitive(not busy)
        self._host_entry.set_sensitive(not busy)
        self._port_entry.set_sensitive(not busy)
        self._use_tls_switch.set_sensitive(not busy)
        self._find_servers_button.set_sensitive(not busy)
        self._login_button.set_sensitive(not busy)

        # Toggle login spinner animation...
        self._login_spinner.set_spinning(busy)

