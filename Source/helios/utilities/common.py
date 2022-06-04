#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2022 Cartesian Theatre. All rights reserved.
#

# System imports...
import netifaces
import re
import threading

# Helios...
from helios.utilities import __version__

# Other imports...
from termcolor import colored
from time import sleep
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
        type=int,
        help=_('Port remote server is listening on. Defaults to 6440.'))

    # Define behaviour for --timeout-connect...
    argument_parser.add_argument(
        '--timeout-connect',
        action='store',
        default=None,
        dest='timeout_connect',
        nargs='?',
        type=int,
        help=_('Number of seconds before a connect request times out.'))

    # Define behaviour for --timeout-read...
    argument_parser.add_argument(
        '--timeout-read',
        action='store',
        default=None,
        dest='timeout_read',
        nargs='?',
        type=int,
        help=_('Number of seconds before a read times out.'))

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
                print(_(F"Helios server {colored(_('online'), 'green')} (no service information available)"))
                return

            # Extract host and port...
            host = info.parsed_addresses()[0]
            port = info.port
            tls  = bool(re.match(self._service_tls_regex, name) is not None)

            # Add to available list, if not already...
            if not self._servers.count((host,port,tls)):
                self._servers.append((host,port,tls))

            # Notify user...
            if re.match(self._service_tls_regex, name) is not None:
                print(_(F"Helios server {colored(_('online'), 'green')} at {host}:{port} ({colored(_('TLS'), 'green')})"))
            else:
                print(_(F"Helios server {colored(_('online'), 'green')} at {host}:{port} ({colored(_('TLS disabled'), 'red')})"))

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
            print(_(F"Helios server {colored(_('offline'), 'yellow')} (no service information available)"))
            return

        # Extract host and port...
        host = info.parsed_addresses()[0]
        port = info.port

        # Remove from available list if it was already there...
        for server in self._servers:
            if (server[0] is host) and (server[1] is port):
                self._servers.remove(server)

        # If nothing is available, clear event flag...
        if len(self._servers) == 0:
            self.found_event.clear()

    # Get server list of all servers found...
    def get_found(self):
        return self._servers

    # Service updated callback...
    def update_service(self, zeroconf, type, name):
        pass


# Find the first available Helios server on the local network and return its
#  host and port...
def zeroconf_find_server():

    # Alert user...
    print(_("Searching LAN for Helios servers... (ctrl-c to cancel)"))

    # Initialize Zeroconf...
    zeroconf = Zeroconf()

    # Construct listener...
    listener = LocalNetworkServiceListener()

    # Begin listening...
    ServiceBrowser(zc=zeroconf, type_="_http._tcp.local.", listener=listener)
    ServiceBrowser(zc=zeroconf, type_="_https._tcp.local.", listener=listener)

    # Wait until it finds a server...
    listener.found_event.wait()

    # Wait for another. This drastically increases the odds of mitigating a race
    #  condition whereby the user wants the service running on a local
    #  interface, but we end up discovering an externally running service
    #  first...
    listener.found_event.clear()
    listener.found_event.wait(1.0)

    # Cleanup...
    zeroconf.close()

    # Get list of detected servers...
    server_list = listener.get_found()

    # If we don't find a better server, use the first one detected...
    best_server = server_list[0]

    # Set of all local IP addresses...
    local_ip_addresses = set()

    # Get a set of all available local IP addresses. Traverse each interface by
    #  name...
    for interface_name in netifaces.interfaces():

        # Traverse each set of address types on the given named interface...
        for address_family in netifaces.ifaddresses(interface_name):

            # We're only interested in IPv4 or IPv6 addresses...
            if (address_family != netifaces.AF_INET):# and (address_family != netifaces.AF_INET6):
                continue

            # Get list of addresses of given type on the given interface...
            interface_addresses = netifaces.ifaddresses(interface_name)[address_family]

            # Each interface can have multiple addresses of the same address
            #  family. Go through each for this address family and extract out
            #  the interface IP address...
            for interface in interface_addresses:
                if 'addr' in interface:
                    local_ip_addresses.add(interface['addr'])

#    print(F"All local IP addresses: {local_ip_addresses}")

    # But if multiple were found. Select the local host, if present...
    if len(server_list) > 1:

        # Search through list of detected servers...
        for (host, port, tls) in server_list:

#            print("{host} in local_ip_addresses: {host in local_ip_addresses}")

            # Found one bound to a local interface...
            if host in local_ip_addresses:

                # Notify user of our choice...
                print(_(F"Multiple detected. Defaulting to local: {host}:{port}"))

                # Save best selection...
                best_server = (host, port, tls)

                # Stop at first local find...
                break

    # Return host, port, and TLS flag of first found...
    return best_server


# Get utilities package version...
def get_version():
    return __version__.version
