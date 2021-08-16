#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2021 Cartesian Theatre. All rights reserved.
#

# System imports...
import sys
from time import sleep

# Other imports...
from helios.utilities.common import LocalNetworkServiceListener
from zeroconf import ServiceBrowser, Zeroconf

# i18n...
import gettext
_ = gettext.gettext

# Main function...
def main():

    # Try to query server status...
    success = False
    try:

        # Alert user...
        print("Probing LAN for all Helios servers... (ctrl-c to abort)")

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
    except Exception as some_exception:
        print(_(f"An unknown exception occurred: {print(some_exception)}"))

    # If unsuccessful, bail...
    if not success:
        sys.exit(1)

    # Done...
    sys.exit(0)

# Entry point...
if __name__ == '__main__':
    main()
