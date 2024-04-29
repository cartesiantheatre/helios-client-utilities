#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2024 Cartesian Theatre. All rights reserved.
#

# System imports...
import sys
from time import sleep

# Other imports...
from helios_client_utilities.common import LocalNetworkHeliosServiceListener
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
        print(_("Searching LAN for Helios servers... (ctrl-c to cancel)"))

        # Initialize Zeroconf...
        zeroconf = Zeroconf()

        # Construct listener...
        helios_listener = LocalNetworkHeliosServiceListener()

        # Begin listening...
        browser = ServiceBrowser(zc=zeroconf, type_="_http._tcp.local.", listener=helios_listener)
        browser_tls = ServiceBrowser(zc=zeroconf, type_="_https._tcp.local.", listener=helios_listener)

        # Keep blocking while scanning...
        try:
            while True:
                sleep(0.1)

        # Unless the user requests to abort...
        except KeyboardInterrupt:
            print(_(F"\rAborting, please wait..."))

        # Cleanup Zeroconf...
        finally:
            browser.cancel()
            browser_tls.cancel()
            zeroconf.close()

        # Set exit status...
        success = True

    # Some other kind of exception...
    except Exception as some_exception:
        print(_(F"An unknown exception occurred: {print(some_exception)}"))

    # If unsuccessful, bail...
    if not success:
        sys.exit(1)

    # Done...
    sys.exit(0)

# Entry point...
if __name__ == '__main__':
    main()
