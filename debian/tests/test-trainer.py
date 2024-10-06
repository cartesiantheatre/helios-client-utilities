#!/usr/bin/env -S python3 -Werror
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2024 Cartesian Theatre. All rights reserved.
#

# System imports...
import os
import subprocess
import sys

# Start D-Bus in a headless environment...
def start_dbus():

    # This test needs a DISPLAY, so if we don't have one, run ourselves via
    # xvfb-run...
    if "DISPLAY" not in os.environ:

        # Ignore the user's .Xauthority file, if any...
        os.environ["XAUTHORITY"] = "/dev/null"

        # Restart ourself within a virtual frame buffer...
        subprocess.check_call(
            [
                "xvfb-run",
                "--auto-servernum"
            ] + sys.argv, env=os.environ)

        # Exit and let the new process continue...
        exit()

    # Create two pipes that dbus-daemon(1) will write its new session's address
    #  and PID to...
    pid_r, pid_w = os.pipe()
    addr_r, addr_w = os.pipe()

    # Allow child processes to inherit these file descriptors...
    os.set_inheritable(pid_w, True)
    os.set_inheritable(addr_w, True)

    # Create the new D-Bus session, but don't automatically close i/o pipes
    #  after it forks...
    subprocess.check_call(
        [
            "dbus-daemon",
            "--fork",
            "--session",
            "--print-address=%d" % addr_w,
            "--print-pid=%d" % pid_w,
        ],
        close_fds=False
    )

    # Close the two write pipes because we are done with them...
    os.close(pid_w)
    os.close(addr_w)

    # Extract the session PID and address from the pipes...
    dbuspid = int(os.read(pid_r, 4096).decode("ascii").strip())
    dbusaddr = os.read(addr_r, 4096).decode("ascii").strip()

    # Close the two read pipes because we have what we need now...
    os.close(pid_r)
    os.close(addr_r)

    # Set an environment variable that notes where to find the new D-Bus
    #  session...
    os.environ["DBUS_SESSION_BUS_ADDRESS"] = dbusaddr

# Enable Assistive Technology support which dogtail needs...
def enable_a11y():

    subprocess.check_call(
        [
            "gsettings",
            "set",
            "org.gnome.desktop.interface",
            "toolkit-accessibility",
            "true",
        ]
    )

# Entry point...
if __name__ == '__main__':

    # Configure environment variables...
    os.environ["LC_ALL"] = 'C.UTF-8'
    os.environ['LANG'] = 'en_CA.UTF-8'
    os.environ['GTK_MODULES'] = 'gail:atk-bridge'

    # Start D-Bus in a headless environment...
    start_dbus()

    # Enable Assistive Technology support which dogtail needs...
    enable_a11y()

    # Now we can import Dogtail...
    from dogtail import tree
    from dogtail.utils import run
    from dogtail.procedural import focus, click
    from dogtail.rawinput import keyCombo

    # Launch the trainer...
    run('helios-trainer', timeout=10)

    # Focus application. This doesn't actually "focus" it, but just sets a
    #  pointer inside the dogtail library...
    focus.application('helios-trainer')

    # Uncomment to see UI layout as seen from the library...
    #trainer = tree.root.application('helios-trainer')
    #trainer.dump()

    # TODO: Figure out how to interact with the various UI elements. Dogtail is
    #  not very well documented...

    # Close it...
    keyCombo('<Alt>F4')

    # Report success to the shell...
    sys.exit(0)

