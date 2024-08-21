#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2024 Cartesian Theatre. All rights reserved.
#

# System imports...
import argparse
from pprint import pprint
import sys

# Other imports....
import attr
import helios
from helios_client_utilities.common import add_common_arguments, zeroconf_find_server
from termcolor import colored

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

    # Try to query server status...
    success = False
    try:

        # If no host provided, use Zeroconf auto detection...
        if not arguments.host:
            
            # Get the list of all IP addresses for every interface for the best
            #  server, its port, and TLS flag...
            addresses, arguments.port, arguments.tls = zeroconf_find_server()

            # Select the first interface on the server...
            arguments.host = addresses[0]

        # Create a client...
        client = helios.Client(
            host=arguments.host,
            port=arguments.port,
            api_key=arguments.api_key,
            timeout_connect=arguments.timeout_connect,
            timeout_read=arguments.timeout_read,
            tls=arguments.tls,
            tls_ca_file=arguments.tls_ca_file,
            tls_certificate=arguments.tls_certificate,
            tls_key=arguments.tls_key,
            verbose=arguments.verbose)

        # Get server status...
        system_status = client.get_system_status()

        # Get server genres information...
        genres_information_list = client.get_genres_information()

        # Signal to shell everything was fine...
        success = True

    # Helios exception...
    except helios.exceptions.ExceptionBase as some_exception:
        print(some_exception.what())

    # User trying to abort...
    except KeyboardInterrupt:
        print(_('\rAborting, please wait a moment...'))

    # Some other kind of exception...
    except Exception as some_exception:
        print(_(F"An unknown exception occurred: {type(some_exception)}"))

    # Show server information if received and verbosity enabled...
    if success and arguments.verbose:
        pprint(attr.asdict(system_status))

    # Show server catalogue information...
    if success:

        # Show how many songs in catalogue...
        print(_(F"Server has {format(system_status.songs, ',d')} songs:"))

        # Add some white space...
        print('')

        # Show song histogram arranged by genre...
        for genre_information in genres_information_list:

            # If no genre available, annotate as such...
            if not genre_information.genre:
                genre_information.genre = _("(Unknown)")

            # Show genre and total number of songs belonging to it...
            print(F"{genre_information.genre:>16} : {genre_information.count:<10}")

        # Add some trailing white space...
        print('')

    # Some problem occurred...
    else:
        print(F"{colored(_('There was a problem verifying the server status.'), 'red')}")

    # If unsuccessful, bail...
    if not success:
        sys.exit(1)

    # Done...
    sys.exit(0)

# Entry point...
if __name__ == '__main__':
    main()

