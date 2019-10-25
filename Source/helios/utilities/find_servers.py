#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2019 Cartesian Theatre. All rights reserved.
#

# Our imports...
import helios
from helios.utilities.common import LocalNetworkServiceListener

# System imports...
from pprint import pprint
import argparse
import attr
import colorama
import datetime
import sys
from time import sleep

# Zeroconf...
from zeroconf import ServiceBrowser, Zeroconf

# i18n...
import gettext
_ = gettext.gettext

# Main function...
def main():

    # Initialize terminal colour...
    colorama.init()

    # Try to query server status...
    success = False
    try:

        # Alert user...
        print(F'Probing LAN for all Helios servers... (ctrl-c to abort)')

        # Initialize Zeroconf...
        zeroconf = Zeroconf()

        # Construct listener...
        listener = LocalNetworkServiceListener()

        # Begin listening...
        browser = ServiceBrowser(zc=zeroconf, type_="_http._tcp.local.", listener=listener)
        browser_tls = ServiceBrowser(zc=zeroconf, type_="_https._tcp.local.", listener=listener)

        # Keep blocking while scanning...
        try:
            while True:
                sleep(0.1)

        # Unless the user requests to abort...
        except KeyboardInterrupt:
            print('\rAborting, please wait...')

        # Cleanup Zeroconf...
        finally:
            browser.cancel()
            browser_tls.cancel()
            zeroconf.close()

        # Remember that we were successful...
        success = True

    # Some other kind of exception...
    except Exception as someException:
        print(_(f"An unknown exception occurred: {print(someException)}"))

    # If unsuccessful, bail...
    if not success:
        sys.exit(1)

    # Done...
    sys.exit(0)

# Entry point...
if __name__ == '__main__':
    main()

