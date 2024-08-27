#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2024 Cartesian Theatre. All rights reserved.
#

# System imports...
from datetime import datetime
import ipaddress
import json
import netifaces
import re
import threading

# Helios...
from helios_client_utilities import __version__

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
class LocalNetworkHeliosServiceListener:

    # Constructor...
    def __init__(self, logging=True, add_callback=None, remove_callback=None, sane_ips=True):
        self._logging           = logging
        self._add_callback      = add_callback
        self._remove_callback   = remove_callback
        self._sane_ips          = sane_ips
        self.found_event        = threading.Event()
        self._servers           = []
        self._name_regex        = r'^Helios(\s\#\d*)?\._http(s)?\._tcp\.local\.$'
        self._service_tls_regex = r'^Helios(\s\#\d*)?\._https\._tcp\.local\.$'

    # Service online callback...
    def add_service(self, zeroconf, type_, name):

        # Which service?
        info = zeroconf.get_service_info(type_, name)

        # Found server...
        if re.match(self._name_regex, name) is not None:

            # No network service information available...
            if info is None:

                # Log, if requested...
                if self._logging:
                    print(_(F"Helios server {colored(_('online'), 'green')} (no service information available)"))

                # Nothing more to do...
                return

            # Extract fully qualified name for service, address list, and port for this service...
            server      = info.server
            addresses   = info.parsed_addresses()
            port        = info.port
            tls         = bool(re.match(self._service_tls_regex, name) is not None)

            # Sane mode enabled. Remove loopback and link local IP addresses...
            if self._sane_ips is True:

                # Remove link local...
                addresses = list(filter(lambda host: not ipaddress.ip_address(host).is_link_local, addresses))

                # Remove loopback...
                addresses = list(filter(lambda host: not ipaddress.ip_address(host).is_loopback, addresses))

                # Remove reserved...
                addresses = list(filter(lambda host: not ipaddress.ip_address(host).is_reserved, addresses))

            # If not already known...
            if not self._servers.count((addresses, port, tls)):

                # Add to available list...
                self._servers.append((server, addresses, port, tls))

                # Invoke user callback, if provided...
                if self._add_callback is not None:
                    self._add_callback(server, addresses, port, tls)

            # Prepare message to notify user...
            if re.match(self._service_tls_regex, name) is not None:
                message = _(F"Helios server {colored(_('online'), 'green')} {server} ({colored(_('TLS'), 'green')})")

            else:
                message = _(F"Helios server {colored(_('online'), 'green')} {server} ({colored(_('TLS disabled'), 'red')})")

            # Log, if requested...
            if self._logging:

                # Show basic info...
                print(message)

                # Show available interface for host and port...
                for address in addresses:
                    print(F'  {address}:{port}')

            # Alert any waiting threads at least one server is found...
            self.found_event.set()

    # Service went offline callback...
    #  TODO: This callback doesn't know which server went offline. It only knows
    #  the service name. Potential solution here:
    #  <https://github.com/python-zeroconf/python-zeroconf/issues/1235>
    def remove_service(self, zeroconf, type_, name):

        # Which service?
        info = zeroconf.get_service_info(type_, name)

        # Not a Helios server...
        if re.match(self._name_regex, name) is None:
            return

        # No network service information available...
        if info is None:

            # Log, if requested...
            if self._logging:
                print(_(F"Helios server {colored(_('offline'), 'yellow')} (no service information available)"))

            # Invoke user's callback, if requested...
#            if self._remove_callback is not None:
#                self._remove_callback(host, port)

            # Done...
            return

        # Extract fully qualified name for service, address list, and port for
        #  this service...
        server      = info.server
        addresses   = info.parsed_addresses()
        port        = info.port

        # Remove from available list...
        for server in self._servers:

            # If it was already there, remove from available list...
            if (server[0] is server) and (server[2] is port):
                self._servers.remove(server)

        # If nothing is available, clear event flag...
        if len(self._servers) == 0:
            self.found_event.clear()

    # Get server list of all servers found...
    def get_found(self):
        return self._servers

    # Service updated callback...
    def update_service(self, zeroconf, type_, name):
        #print('update_service')
        pass


# Training session class...
class TrainingSession:

    # Constructor...
    def __init__(self):

        # Initialize session to defaults...
        self.reset()

    # Add a triplet example...
    def add_example(self, anchor: str, positive: str, negative: str):

        # Construct dictionary of example...
        example = {
            'anchor'    : anchor,
            'positive'  : positive,
            'negative'  : negative
        }

        # Add dictionary to list of triplets...
        self._triplets.append(example)

    # Get a set of references for every song listened to...
    def get_all_song_references(self):

        # Set containing every unique song reference from every learning example
        #  triplet...
        all_songs_listened_to = set()

        # Add each song's reference to the set...
        for learning_example_triplet in self._triplets:
            all_songs_listened_to.add(learning_example_triplet['anchor'])
            all_songs_listened_to.add(learning_example_triplet['positive'])
            all_songs_listened_to.add(learning_example_triplet['negative'])

        # Return the set to caller...
        return all_songs_listened_to

    # Get API key...
    def get_api_key(self) -> str:
        return self._api_key

    # Get datetime...
    def get_datetime(self) -> str:
        return self._datetime

    # Get expert email...
    def get_expert_email(self) -> str:
        return self._expert_email

    # Get expert name...
    def get_expert_name(self) -> str:
        return self._expert_name

    # Get host...
    def get_host(self) -> str:
        return self._host

    # Get path...
    def get_path(self) -> str:
        return self._path

    # Get port...
    def get_port(self) -> int:
        return self._port

    # Get use TLS flag...
    def get_tls(self) -> bool:
        return self._tls

    # Get the total number of examples...
    def get_total_examples(self):
        return len(self._triplets)

    # Get the list of triplets...
    def get_examples(self):
        return self._triplets

    # Get the total number of songs the expert listened to...
    def get_total_songs_listened(self):

        # Get set containing every unique song reference from every learning
        #  example triplet...
        all_songs_listened_to = self.get_all_song_references()

        # Return the total number of songs listened to...
        return len(all_songs_listened_to)

    # Get Helios server version...
    def get_version(self) -> str:
        return self._version

    # Load from disk...
    def load(self, path: str):

        # Initialize session to defaults...
        self.reset()

        # If path provided by caller, use it...
        if path is not None:
            self.set_path(path)

        # Storage for parsed JSON...
        json_object = None

        # Try to read from disk...
        try:
            with open(self._path, 'r') as infile:
                json_object = json.load(infile)

        # Failed...
        except json.decoder.JSONDecodeError as some_exception:
            raise Exception(F'File is either corrupt or not an .hts file!')

        # Make sure there is a format version field...
        if 'helios-training-session-format' not in json_object:
            raise Exception(F'Unknown training session file format!')

        # Get the file format version...
        format_written = json_object['helios-training-session-format']

        # We can only understand a specific version...
        if self._format != format_written:
            raise Exception(F'Incompatible training session format! Expected format version {self._format}, but found {format_written}.')

        # Read basic fields...
        self._expert_email  = json_object['expert_email']
        self._expert_name   = json_object['expert_name']
        self._api_key       = json_object['api-key']
        self._datetime      = json_object['datetime']
        self._host          = json_object['host']
        self._port          = json_object['port']
        self._tls           = json_object['tls']
        self._version       = json_object['version']

        # Load each example...
        for example in json_object['examples']:

            # Read the triplet...
            anchor      = example['anchor']
            positive    = example['positive']
            negative    = example['negative']

            # Load triplet example into session...
            self.add_example(anchor, positive, negative)

    # Clear session and restore defaults...
    def reset(self):

        # Path to session on disk...
        self._path          = None

        # This is the file format version that is understood...
        self._format        = 1

        # Initialize attributes to defaults for basic metadata...
        self._api_key       = None
        self._datetime      = None
        self._expert_email  = None
        self._expert_name   = None
        self._host          = None
        self._port          = None
        self._tls           = None
        self._version       = None

        # Set of user's triplets...
        self._triplets      = list()

    # Save to disk...
    def save(self, path: str=None):

        # If path provided by caller, save it. Otherwise use last saved
        #  location...
        if path is not None:
            self.set_path(path)

        # Update save datetime...
        self._datetime = datetime.now().isoformat()

        # Construct dictionary of data to be written out...
        dictionary = {
            'helios-training-session-format'    : self._format,
            'api-key'                           : self._api_key,
            'datetime'                          : self._datetime,
            'expert_email'                      : self._expert_email,
            'expert_name'                       : self._expert_name,
            'host'                              : self._host,
            'port'                              : self._port,
            'tls'                               : self._tls,
            'version'                           : self._version,
            'examples'                          : self._triplets
        }

        # Serialize to JSON...
        json_object = json.dumps(dictionary, indent=4)

        # Write to disk...
        with open(self._path, 'w') as outfile:
            outfile.write(json_object)

    # Set API key...
    def set_api_key(self, api_key: str):
        self._api_key = api_key

    # Set expert email...
    def set_expert_email(self, expert_email: str):
        self._expert_email = expert_email

    # Set expert name...
    def set_expert_name(self, expert_name: str):
        self._expert_name = expert_name

    # Set host...
    def set_host(self, host: str):
        self._host = host

    # Set path to save on disk...
    def set_path(self, path: str):
        self._path = path

    # Set port...
    def set_port(self, port: int):
        self._port = port

    # Set use TLS flag...
    def set_tls(self, tls: bool):
        self._tls = tls

    # Set version of Helios server...
    def set_version(self, version: str):
        self._version = version


# Find the first available Helios server on the local network and return a tuple
#  ip_address, port, and TLS capability. Set wait_time to maximum time to look
#  for a server, or None to wait indefinitely...
def zeroconf_find_server(wait_time=None):

    # Alert user...
    print(_("Searching LAN for Helios servers... (ctrl-c to cancel)"))

    # Initialize Zeroconf...
    zeroconf = Zeroconf()

    # Construct listener...
    helios_listener = LocalNetworkHeliosServiceListener()

    # Begin listening...
    ServiceBrowser(zc=zeroconf, type_="_http._tcp.local.", listener=helios_listener)
    ServiceBrowser(zc=zeroconf, type_="_https._tcp.local.", listener=helios_listener)

    # User is fine waiting indefinitely for first discovery...
    if wait_time is None:

        # Wait until it finds a server...
        helios_listener.found_event.wait()

        # Wait for another. This drastically increases the odds of mitigating a
        #  race condition whereby the user wants the service running on a local
        #  interface, but we end up discovering an externally running service
        #  first...
        helios_listener.found_event.clear()
        helios_listener.found_event.wait(1.0)

    # Otherwise wait no longer than requested...
    else:

        # Wait until it finds a server...
        helios_listener.found_event.wait(wait_time)

    # Cleanup...
    zeroconf.close()

    # Get list of detected servers...
    server_list = helios_listener.get_found()

    # Found nothing...
    if not len(server_list):
        raise Exception(_('No Helios servers found.'))

    # If we don't find a better server, use the first one detected, removing
    #  fully qualified name to just provide IP addresses...
    server          = server_list[0]
    best_address    = server[1]
    port            = server[2]
    tls             = server[3]
    best_server     = (best_address, port, tls)

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

    # But if multiple servers were found, select the local host if present...
    if len(server_list) > 1:

        # Search through list of detected servers...
        for (server, addresses, port, tls) in server_list:

#            print("{address} in local_ip_addresses: {address in local_ip_addresses}")

            # Examine each IP address the server advertised...
            for address in addresses:

                # Found one bound to a local interface...
                if address in local_ip_addresses:

                    # Notify user of our choice...
                    print(_(F"Multiple detected. Automatically selecting self: {address}:{port}"))

                    # Save best selection...
                    best_server = (address, port, tls)

                    # Stop at first local find...
                    break

    # Return best address, port, and TLS flag of first found...
    return best_server


# Get utilities package version...
def get_version():
    return __version__.version
