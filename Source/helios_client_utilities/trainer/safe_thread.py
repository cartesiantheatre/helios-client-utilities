#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2024 Cartesian Theatre. All rights reserved.
#

# System imports...
import threading

# i18n...
import gettext
_ = gettext.gettext

# Thread class that can raise exceptions within the thread that invoked the new
#  thread...
class SafeThread(threading.Thread):

    # Constructor...
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, daemon=None):

        # Initialize base class...
        super().__init__(group=group, target=target, name=name, daemon=daemon)

        # Save user's callable object...
        self._target     = target

        # Field which stores exception raised within thread, if any...
        self._exception  = None

    # Join thread...
    def join(self, timeout=None):

        # Wait for thread to complete...
        threading.Thread.join(self, timeout)

        # If any exception was raised within the thread, we re-raise it within
        #  the calling thread...
        if self._exception:
            raise self._exception

    # Invoke the callable object passed to constructor in a new thread.
    #  Overrides baseclass's implementation...
    def run(self, *args, **kwargs):

        # Try to run the user's callable object...
        try:

            # If no callable object was provided, this is an error...
            if self._target is None:
                raise Exception(_('You must override SafeThread.entry_point.'))

            # Otherwise invoke the user's callable object...
            self._target(*args, **kwargs)

        # Something bad happened...
        except Exception as some_exception:

            # Save the exception to raise later when user joins thread...
            self._exception = some_exception

