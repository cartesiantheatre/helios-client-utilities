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

# Other imports...
from termcolor import colored
from zeroconf import ServiceBrowser, Zeroconf

# i18n...
import gettext
_ = gettext.gettext

# Add common arguments to argument parser...
def add_common_arguments(argument_parser):

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

    # Define behaviour for --token...
    argument_parser.add_argument(
        '--token',
        action='store',
        default=None,
        dest='token',
        help=_('Client API token to submit to remote server with each request. '
               'This may or may not be required, depending on your server\'s configuration.'))

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
        self.found_event    = threading.Event()
        self._servers       = []
        self._name_regex    = r'^Helios(\s\#\d*)?\._http\._tcp\.local\.$'

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

            # Add to available list, if not already...
            if not self._servers.count((host,port)):
                self._servers.append((host,port))

            # Notify user...
            print(F"Helios server {colored(_('online'), 'green')} at {host}:{port}")

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
        while self._servers.count((host,port)):
            self._servers.remove((host,port))

        # If nothing is available, clear event flag...
        if not len(self._servers):
            self.found_event.clear()

    # Get host and port list of all servers found...
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
    browser = ServiceBrowser(zeroconf, "_http._tcp.local.", listener)

    # Wait until it finds server...
    listener.found_event.wait()

    # Cleanup...
    zeroconf.close()

    # Return host and port of first found...
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
    return '0.5.dev20190920'

