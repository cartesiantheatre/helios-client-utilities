#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2024 Cartesian Theatre. All rights reserved.
#

# System imports...
from time import sleep

# Gtk related imports...
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gio, GObject, GLib

# Helios...
from helios_client_utilities.trainer import *

# Zeroconf...
from zeroconf import ServiceBrowser, Zeroconf

# i18n...
import gettext
_ = gettext.gettext

# A row to be stored within a Gio.ListStore data structure...
class FoundServer(GObject.Object):

    __gtype_name__ = "FoundServer"

    # Constructor...
    def __init__(self, server: str, address: str, port: int, tls: bool):

        # Initialize base class...
        super().__init__()

        # Store fields...
        self._server    = server
        self._address   = address
        self._port      = port
        self._tls       = tls

    # Property accessor for server...
    @GObject.Property(type=str, default='')
    def server(self):
        return self._server

    # Property accessor for address...
    @GObject.Property(type=str, default='')
    def address(self):
        return self._address

    # Property accessor for port...
    @GObject.Property(type=int, default=0)
    def port(self):
        return self._port

    # Property accessor for TLS...
    @GObject.Property(type=bool, default=False)
    def tls(self):
        return self._tls

    # Return string representation of object...
    def __repr__(self):
        return F'FoundServer(server={self._server}, address={self._address}, port={self._port}, tls={self._tls})'


# Main window class...
class FindServersWindow(Gtk.Window):

    # Constructor...
    def __init__(self, login_page, *args, **kwargs):

        # Initialize base class...
        super().__init__(*args, **kwargs)

        # Get the application...
        self._application = self.get_application()

        # Save main window...
        self._login_page = login_page

        # Set modal...
        self.set_modal(True)

        # Set the default size...
        self.set_default_size(700, 300)

        # Set window title...
        self.set_title(_('Find Helios Servers'))

        # When user requests to close window, invoke callback...
        self.connect('close-request', self.on_close_request)

        # Construct master sizer...
        master_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        master_vbox.set_margin_top(10)
        master_vbox.set_margin_start(10)
        master_vbox.set_margin_bottom(10)
        master_vbox.set_margin_end(10)
        master_vbox.set_vexpand(True)

        # Server model...
        self._list_store_model = Gio.ListStore(item_type=FoundServer)
#        self._list_store_model.append(FoundServer('demobackend.heliosmusic.io', 6440, True))
#        self._list_store_model.append(FoundServer('localhost', 12345, False))
        self._list_store_model.connect('items-changed', self.on_list_store_items_changed)

        # Server column server factory...
        self._server_factory = Gtk.SignalListItemFactory()
        self._server_factory.connect('setup', self.on_factory_setup, 'server')
        self._server_factory.connect('bind', self.on_factory_bind, 'server')

        # Address column server factory...
        self._address_factory = Gtk.SignalListItemFactory()
        self._address_factory.connect('setup', self.on_factory_setup, 'address')
        self._address_factory.connect('bind', self.on_factory_bind, 'address')

        # Port column server factory...
        self._port_factory = Gtk.SignalListItemFactory()
        self._port_factory.connect('setup', self.on_factory_setup, 'port')
        self._port_factory.connect('bind', self.on_factory_bind, 'port')

        # TLS column server factory...
        self._tls_factory = Gtk.SignalListItemFactory()
        self._tls_factory.connect('setup', self.on_factory_setup, 'tls')
        self._tls_factory.connect('bind', self.on_factory_bind, 'tls')

        # Server single selection...
        self._single_selection = Gtk.SingleSelection(model=self._list_store_model)
        self._single_selection.connect('selection-changed', self.on_selection_change)

        # Create server column view...
        self._column_view = Gtk.ColumnView()
        self._column_view.set_model(self._single_selection)
        self._column_view.set_show_column_separators(True)
        self._column_view.set_show_row_separators(True)
        self._column_view.set_vexpand(True)
        self._column_view.set_hexpand(True)
        self._column_view.connect('activate', self.on_server_activate)

        # Create server column...
        column = Gtk.ColumnViewColumn(title=_('Server'), factory=self._server_factory)
        column.set_resizable(True)
        column.set_expand(True)
        self._column_view.append_column(column)

        # Create address column...
        column = Gtk.ColumnViewColumn(title=_('IP Address'), factory=self._address_factory)
        column.set_resizable(True)
        column.set_expand(True)
        self._column_view.append_column(column)

        # Create port column...
        column = Gtk.ColumnViewColumn(title=_('Port'), factory=self._port_factory)
        column.set_resizable(True)
        column.set_fixed_width(120)
        self._column_view.append_column(column)

        # Create TLS column...
        column = Gtk.ColumnViewColumn(title=_('TLS'), factory=self._tls_factory)
        column.set_resizable(True)
        column.set_fixed_width(100)
        self._column_view.append_column(column)

        # Put column view within a scrolled window...
        scrolled_window = Gtk.ScrolledWindow.new()
        scrolled_window.set_child(self._column_view)

        # Add server column view widget to master sizer...
        master_vbox.append(scrolled_window)

        # Create spinner...
        spinner = Gtk.Spinner(tooltip_text=_('Probing your local area network for Helios servers...'))
        spinner.start()
        spinner.set_size_request(30, 30)

        # Create cancel button...
        self._cancel_button = Gtk.Button(label=_("Cancel"), tooltip_text=_('Cancel'))
        self._cancel_button.connect('clicked', self.on_cancel_button)

        # Create select button...
        self._select_button = Gtk.Button(label=_("Select"), tooltip_text=_('Use selected server'))
        self._select_button.set_sensitive(False)
        self._select_button.connect('clicked', self.on_select_button)

        # Create sizer for refresh and select buttons...
        buttons_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        buttons_hbox.set_valign(Gtk.Align.CENTER)
        buttons_hbox.set_halign(Gtk.Align.END)
        buttons_hbox.set_margin_top(10)
        buttons_hbox.set_margin_start(10)
        buttons_hbox.set_margin_bottom(10)
        buttons_hbox.set_margin_end(10)

        # Add refresh and select buttons into button sizer...
        buttons_hbox.append(spinner)
        buttons_hbox.append(self._cancel_button)
        buttons_hbox.append(self._select_button)

        # Add refresh buttons sizer and its children into main vertical box...
        master_vbox.append(buttons_hbox)

        # Add master sizer and all of its children to window...
        self.set_child(master_vbox)

        # Flag to signal to discovery thread time to exit...
        self._close_request = False

        # Spawn discovery thread...
        self._discovery_thread = SafeThread(target=self.discovery_thread)
        self._discovery_thread.start()

    # User wants to close window...
    def on_close_request(self, window):

        # Signal to discovery thread time to exit...
        self._close_request = True

        # Wait for discovery thread to finish...
        self._discovery_thread.join()

        # Returning false allows window to close...
        return False

    # Server discovery thread...
    def discovery_thread(self):

        # Initialize Zeroconf...
        zeroconf = Zeroconf()

        # Construct listener...
        listener = LocalNetworkHeliosServiceListener(
            logging=False,
            add_callback=self.on_zeroconf_add_server,
            remove_callback=self.on_zeroconf_remove_server)

        # Begin listening...
        browser = ServiceBrowser(zc=zeroconf, type_="_http._tcp.local.", listener=listener)
        browser_tls = ServiceBrowser(zc=zeroconf, type_="_https._tcp.local.", listener=listener)

        # Scan at tenth of a second intervals until close requested...
        while not self._close_request:
            sleep(0.1)

        # Cleanup...
        zeroconf.close()

    # Cancel button clicked...
    def on_cancel_button(self, button):

        # Close window...
        self.close()

    # Factory is preparing to setup a widget or widgets in the row to add to
    #  list_item...
    def on_factory_setup(self, factory, list_item, what):

        # Widget to compose the cell we are trying to setup...
        widget = None

        # Which kind of cell are we trying to create?
        match what:

            # Server cell. Construct a label...
            case 'server':
                widget = Gtk.Label()

            # Address cell. Construct a label...
            case 'address':
                widget = Gtk.Label()

            # Port cell. Construct a label...
            case 'port':
                widget = Gtk.Label()

            # TLS cell. Construct an image...
            case 'tls':
                widget = Gtk.Image.new()
                widget.set_pixel_size(25)

        # This field will eventually be bound to the correct property in the
        #  FoundServer object such that changing the property in it will
        #  automatically update the target value in the label widget...
        widget._binding = None

        # Set it as the child for the item. During bind it will be populated
        #  with the actually appropriate text...
        list_item.set_child(widget)

    # Bind the data to the widgets in the list_item. This is called for every
    #  cell in every row to actually populate the widgets with the data...
    def on_factory_bind(self, factory, list_item, what):

        # Widget to compose the cell we are trying to setup...
        widget = list_item.get_child()

        # Get the row object...
        found_server_row = list_item.get_item()

        # Which kind of cell are we trying to create?
        match what:

            # Server cell...
            case 'server':

                # Bind the label to the appropriate property (what) in the
                #  FoundServer...
                widget._binding = found_server_row.bind_property(
                    what,
                    widget,
                    'label',
                    GObject.BindingFlags.SYNC_CREATE)

            # Address cell...
            case 'address':

                # Bind the label to the appropriate property (what) in the
                #  FoundServer...
                widget._binding = found_server_row.bind_property(
                    what,
                    widget,
                    'label',
                    GObject.BindingFlags.SYNC_CREATE)

            # Port cell...
            case 'port':

                # Bind the label to the appropriate property (what) in the
                #  FoundServer...
                widget._binding = found_server_row.bind_property(
                    what,
                    widget,
                    'label',
                    GObject.BindingFlags.SYNC_CREATE)

            # TLS cell...
            case 'tls':

                # If the server supports TLS, show a lock icon...
                if found_server_row.tls:
                    widget.set_from_icon_name('changes-prevent')
                    widget.set_tooltip_text(_('TLS encryption enabled.'))

                # If it doesn't, don't show anything...
                else:
                    widget.set_from_icon_name(None)
                    widget.set_tooltip_text(_('TLS encryption disabled.'))

    # Select button clicked...
    def on_select_button(self, button):

        # Retrieve the selected found server...
        position = self._single_selection.get_selected()
        found_server = self._list_store_model.get_item(position)

        # Fill in the server coordinates in the login window...
        self._login_page._host_entry.set_text(found_server.address)
        self._login_page._port_entry.set_text(str(found_server.port))
        self._login_page._use_tls_switch.set_active(found_server.tls)

        # Set focus to login button...
        self._login_page._application_window.set_focus(self._login_page._login_button)

        # Close window...
        self.close()

    # User double clicked a server row...
    #  <https://docs.gtk.org/gtk4/signal.ColumnView.activate.html>
    def on_server_activate(self, column_view, position):

        # Get the selected found server row object...
        #self._selected_found_server = self._list_store_model.get_item(position)
        #print(F'on_server_activate: {self._selected_found_server})')

        # Enable the select button...
        self._select_button.set_sensitive(True)

        # Trigger the select button...
        self._select_button.emit('clicked')

    # User single clicked a server row...
    #  <https://docs.gtk.org/gtk4/signal.SelectionModel.selection-changed.html>
    def on_selection_change(self, selection_model, position, n_items):

        # Enable the select button...
        self._select_button.set_sensitive(True)

        #item_selected = self._single_selection.get_selected()
        #total_items = self._list_store_model.get_n_items()
        #print(F'on_selection_change: {item_selected} of {total_items}')

    # Server list store changed. Rows were either added or removed...
    #  <https://docs.gtk.org/gio/signal.ListModel.items-changed.html>
    def on_list_store_items_changed(self, model, position, removed, added):

        # If the number of items removed differs from the number added then the
        #  position of all later items in the model will have changed...
        if removed != added:

            # Unselect all...
            self._single_selection.unselect_all()

            # Disable select button until user selects something...
            self._select_button.set_sensitive(False)

        # If there are no servers found, disable select button...
        if self._list_store_model.get_n_items() == 0:
            self._select_button.set_sensitive(False)

        # If there is at least one, enable select button...
        else:
            self._select_button.set_sensitive(True)

        # But keep it enabled if some server that remained was still selected...
#        selected_item = self._single_selection.get_selected_item()
#        print(F'on_list_store_items_changed: {selected_item}')
#        if selected_item is not None:
#            self._select_button.set_sensitive(True)

    # Zeroconf discovered a Helios server...
    def on_zeroconf_add_server(self, server, addresses, port, tls):
        #print(F'on_zeroconf_add_server {address}:{port}')

        # Add to server list store model. GUI will automatically be updated...
        for address in addresses:
            GLib.idle_add(
                self._list_store_model.append,
                FoundServer(server, address, port, tls))

    # Zeroconf noted a Helios server just went offline...
    def on_zeroconf_remove_server(self, address, port):
        #print(F'on_zeroconf_remove_server {address}:{port}')

        # TODO: Implement this after getting an answer:
        #  <https://github.com/python-zeroconf/python-zeroconf/issues/1235>
        pass

