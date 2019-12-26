#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2019 Cartesian Theatre. All rights reserved.
#

# System imports...
import argparse
import re
import socket
import threading

# Helios...
from helios.utilities import __version__

# Other imports...
from termcolor import colored
from zeroconf import ServiceBrowser, Zeroconf

# i18n...
import gettext
_ = gettext.gettext

# Add common arguments to argument parser...
def add_common_arguments(argument_parser):

    # Define behaviour for --api-key...
    argument_parser.add_argument(
        '--api-key',
        action='store',
        default=None,
        dest='api_key',
        help=_('Client API key to submit to remote server with each request. '
               'This may or may not be required, depending on your server\'s configuration.'))

    # Define behaviour for --host...
    argument_parser.add_argument(
        '--host',
        action='store',
        default=None,
        dest='host',
        help=_('IP address or host name of remote server. Defaults to auto.'))

    # Define behaviour for --port...
    argument_parser.add_argument(
        '--port',
        action='store',
        default=6440,
        dest='port',
        help=_('Port remote server is listening on. Defaults to 6440.'))

    # Define behaviour for --tls-disabled...
    argument_parser.add_argument(
        '--tls-disabled',
        action='store_false',
        default=True,
        dest='tls',
        help=_('Disable encryption. By default encryption is enabled.'))

    # Define behaviour for --tls-ca-file...
    argument_parser.add_argument(
        '--tls-ca-file',
        action='store',
        default=None,
        dest='tls_ca_file',
        help=_('Verify server\'s certificate is signed by the given certificate authority.'))

    # Define behaviour for --tls-certificate...
    argument_parser.add_argument(
        '--tls-certificate',
        action='store',
        default=None,
        dest='tls_certificate',
        help=_('When encryption is enabled, use this public key.'))

    # Define behaviour for --tls-key...
    argument_parser.add_argument(
        '--tls-key',
        action='store',
        default=None,
        dest='tls_key',
        help=_('When encryption is enabled, use this private key.'))

    # Define behaviour for --verbose...
    argument_parser.add_argument(
        '--verbose',
        action='store_true',
        default=False,
        dest='verbose',
        help=_('Be verbose by showing additional information.'))

    # Define behaviour for --version...
    argument_parser.add_argument(
        '--version',
        action='version',
        version=get_version())

# Zeroconf local network service listener with callbacks to discover Helios
#  server...
class LocalNetworkServiceListener:

    # Constructor...
    def __init__(self):
        self.found_event        = threading.Event()
        self._servers           = []
        self._name_regex        = r'^Helios(\s\#\d*)?\._http(s)?\._tcp\.local\.$'
        self._service_tls_regex = r'^Helios(\s\#\d*)?\._https\._tcp\.local\.$'

    # Service online callback...
    def add_service(self, zeroconf, type, name):

        # Which service?
        info = zeroconf.get_service_info(type, name)

        # Found server...
        if re.match(self._name_regex, name) is not None:

            # No network service information available...
            if info is None:
                print(F"Helios server {colored(_('online'), 'green')} (no service information available)")
                return

            # Extract host and port...
            host = F'{info.address[0]}.{info.address[1]}.{info.address[2]}.{info.address[3]}'
            port = info.port
            tls  = True if re.match(self._service_tls_regex, name) is not None else False

            # Add to available list, if not already...
            if not self._servers.count((host,port,tls)):
                self._servers.append((host,port,tls))

            # Notify user...
            if re.match(self._service_tls_regex, name) is not None:
                print(F"Helios server {colored(_('online'), 'green')} at {host}:{port} ({colored(_('TLS'), 'green')})")
            else:
                print(F"Helios server {colored(_('online'), 'green')} at {host}:{port} ({colored(_('TLS disabled'), 'red')})")

            # Alert any waiting threads at least one server is found...
            self.found_event.set()

    # Service went offline callback...
    def remove_service(self, zeroconf, type, name):

        # Which service?
        info = zeroconf.get_service_info(type, name)

        # Not a Helios server...
        if re.match(self._name_regex, name) is None:
            return

        # No network service information available...
        if info is None:
            print(F"Helios server {colored(_('offline'), 'yellow')} (no service information available)")
            return

        # Extract host and port...
        host = F'{info.address[0]}.{info.address[1]}.{info.address[2]}.{info.address[3]}'
        port = info.port

        # Remove from available list if it was already there...
        for server in self._servers:
            if (server[0] is host) and (server[1] is port):
                self._servers.remove(server)

        # If nothing is available, clear event flag...
        if not len(self._servers):
            self.found_event.clear()

    # Get server list of all servers found...
    def get_found(self):
        return self._servers


# Find the first available Helios server on the local network and return its
#  host and port...
def zeroconf_find_server():

    # Alert user...
    print(F'Probing LAN for a Helios server, please wait...')

    # Initialize Zeroconf...
    zeroconf = Zeroconf()

    # Construct listener...
    listener = LocalNetworkServiceListener()

    # Begin listening...
    browser = ServiceBrowser(zc=zeroconf, type_="_http._tcp.local.", listener=listener)
    browser_tls = ServiceBrowser(zc=zeroconf, type_="_https._tcp.local.", listener=listener)

    # Wait until it finds server...
    listener.found_event.wait()

    # Cleanup...
    browser.cancel()
    browser_tls.cancel()
    zeroconf.close() # TODO: Slow: <https://github.com/jstasiak/python-zeroconf/issues/143>

    # Return host, port, and TLS flag of first found...
    return listener.get_found()[0]

# Return the preferred local IP address...
def get_preferred_local_ip_address():

    # Allocate a temporary connectionless socket...
    temporary_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Try to establish a "connection"...
    try:
        temporary_socket.connect(('10.255.255.255', 1))
        local_ip_address = temporary_socket.getsockname()[0]

    # If it failed, use loopback address...
    except:
        local_ip_address = '127.0.0.1'

    # Close socket...
    finally:
        temporary_socket.close()

    # Return the IP address...
    return local_ip_address

# Get utilities package version...
def get_version():
    return __version__.version

