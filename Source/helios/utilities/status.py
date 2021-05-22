#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2021 Cartesian Theatre. All rights reserved.
#

# System imports...
import helios
from helios.utilities.common import add_common_arguments, zeroconf_find_server
from pprint import pprint
from termcolor import colored
import argparse
import attr
import colorama
import datetime
import sys

# i18n...
import gettext
_ = gettext.gettext

# Main function...
def main():

    # Initialize the argument parser...
    argument_parser = argparse.ArgumentParser(
        description=_('Query the status of a Helios server.'))

    # Add common arguments to argument parser...
    add_common_arguments(argument_parser)

    # Parse the command line...
    arguments = argument_parser.parse_args()

    # Initialize terminal colour...
    colorama.init()

    # Try to query server status...
    success = False
    try:

        # If no host provided, use Zeroconf auto detection...
        if not arguments.host:
            arguments.host, arguments.port, arguments.tls = zeroconf_find_server()

        # Create a client...
        client = helios.client(
            host=arguments.host,
            port=arguments.port,
            api_key=arguments.api_key,
            tls=arguments.tls,
            tls_ca_file=arguments.tls_ca_file,
            tls_certificate=arguments.tls_certificate,
            tls_key=arguments.tls_key,
            verbose=arguments.verbose)

        # Perform query...
        server_status = client.get_server_status()
        success = True

    # Helios exception...
    except helios.exceptions.ExceptionBase as someException:
        print(someException.what())

    # User trying to abort...
    except KeyboardInterrupt:
        print(_('\rAborting, please wait a moment...'))

    # Some other kind of exception...
    except Exception as someException:
        print(_(f"An unknown exception occurred: {type(someException)}"))

    # Show server information if received and verbosity enabled...
    if success and arguments.verbose:
        pprint(attr.asdict(server_status))

    # Show success status or failure...
    if success:
        print(_(f"Server has {server_status.songs} songs."))
    else:
        print(f"{colored(_('There was a problem verifying the server status.'), 'red')}")

    # If unsuccessful, bail...
    if not success:
        sys.exit(1)

    # Done...
    sys.exit(0)

# Entry point...
if __name__ == '__main__':
    main()

