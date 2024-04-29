#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2024 Cartesian Theatre. All rights reserved.
#

# System imports...
import enum
import html
import os
import queue
import tempfile
import threading

# Gtk related imports...
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gio, Gtk, GLib, GdkPixbuf

# Helios...
import helios
from helios_client_utilities.trainer import *

# i18n...
import gettext
_ = gettext.gettext

# Task list enumerated constants...
class TaskList(enum.Enum):
    SELECT_SEARCH_KEY               = 0
    RETRIEVE_SEARCH_KEY_ARTWORK     = 1
    PERFORM_SIMILARITY_SEARCH       = 2
    RETRIEVE_SEARCH_KEY_AUDIO       = 3
    RETRIEVE_ARTWORK_FOR_MATCHES    = 4
    RETRIEVE_AUDIO_FOR_MATCHES      = 5

# Task state enumerated constants...
class TaskState(enum.Enum):
    NOT_STARTED                     = 'NotStarted'
    IN_PROGRESS                     = 'InProgress'
    COMPLETED                       = 'Completed'

# Asset loader page class...
class AssetLoaderPage(StackPage):

    # Constructor...
    def __init__(self, application_window):

        # Initialize base class...
        super().__init__(application_window, name='AssetLoader', title=_('Asset Loader'))

        # Store reference to application window...
        self._application_window = application_window

        # Total number of matches to retrieve for each search key defaults to
        #  eight...
        self._total_matches = 8

        # Unless overridden by user on command line, in which case clamp to
        #  [3, 25] closed interval...
        command_line_dictionary = self._application.get_command_line_dictionary()
        if 'total-matches' in command_line_dictionary:
            total_matches = command_line_dictionary['total-matches']
            self._total_matches = min(max(total_matches, 3), 25)

        # Construct master sizer...
        self._sizer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        self._sizer.set_vexpand(True)
        self._sizer.set_hexpand(True)
        self._sizer.set_valign(Gtk.Align.CENTER)
        self._sizer.set_halign(Gtk.Align.CENTER)
        self._sizer.set_margin_top(20)
        self._sizer.set_margin_start(20)
        self._sizer.set_margin_bottom(20)
        self._sizer.set_margin_end(20)

        # Create search key sizer...
        search_key_sizer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        search_key_sizer.set_vexpand(True)
        self._sizer.append(search_key_sizer)

        # Create search key cover art...
        self._search_key_art = Gtk.Image.new_from_icon_name('image-loading')
        self._search_key_art.set_icon_size(Gtk.IconSize.LARGE)
        self._search_key_art.set_size_request(350, 350)
        self._search_key_art.set_valign(Gtk.Align.CENTER)
        self._search_key_art.set_halign(Gtk.Align.CENTER)
        self._search_key_art.set_margin_top(10)
        self._search_key_art.set_margin_start(10)
        self._search_key_art.set_margin_bottom(10)
        self._search_key_art.set_margin_end(10)
        search_key_sizer.append(self._search_key_art)

        # Create search key title label...
        self._search_key_title_label = Gtk.Label()
        self._search_key_title_label.set_use_markup(True)
        self._search_key_title_label.set_wrap(True)
#        self._search_key_title_label.set_halign(Gtk.Align.CENTER)
        search_key_sizer.append(self._search_key_title_label)

        # Create search key artist label...
        self._search_key_artist_label = Gtk.Label()
#        self._search_key_artist_label.set_halign(Gtk.Align.CENTER)
        self._search_key_artist_label.set_wrap(True)
        search_key_sizer.append(self._search_key_artist_label)

        # Create task list sizer...
        task_list_sizer = Gtk.Grid()
        task_list_sizer.set_vexpand(True)
        task_list_sizer.set_valign(Gtk.Align.CENTER)
        task_list_sizer.set_halign(Gtk.Align.FILL)
        task_list_sizer.set_row_spacing(20)
        task_list_sizer.set_column_spacing(20)
        self._sizer.append(task_list_sizer)

        # List of string tasks to show in download sizer...
        task_list = [
            _('Selecting search key...'),
            _('Retrieving search key artwork...'),
            _('Performing similarity search...'),
            _('Retrieving search key audio...'),
            _(F'Retrieving artwork for matches...'),
            _(F'Retrieving audio for matches...')
        ]

        # List of task stacks that we can manipulate later to transition from
        #  in-progress spinner to completion check mark...
        self._task_stack_list = []

        # Add each task status widget and label to download sizer
        for task_index in range(0, len(task_list)):

            # Create the stack that will hold the spinner and then the
            #  completion check mark when done...
            task_stack = Gtk.Stack()
            task_stack.set_valign(Gtk.Align.FILL)
            task_stack.set_halign(Gtk.Align.FILL)
            task_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
            task_stack.set_transition_duration(100)
            task_list_sizer.attach(task_stack, 0, task_index, 1, 1)

            # Create blank label for not started state...
            task_blank = Gtk.Label()
            task_stack.add_named(task_blank, TaskState.NOT_STARTED.value)

            # Create the spinner for in progress state...
            task_spinner = Gtk.Spinner()
            task_spinner.set_spinning(True)
            task_spinner.set_valign(Gtk.Align.FILL)
            task_spinner.set_halign(Gtk.Align.FILL)
            task_stack.add_named(task_spinner, TaskState.IN_PROGRESS.value)

            # Create the completed icon...
            task_completed_image = Gtk.Image.new_from_icon_name('emblem-default')
            task_completed_image.set_size_request(30, 30)
            task_completed_image.set_valign(Gtk.Align.FILL)
            task_completed_image.set_halign(Gtk.Align.FILL)
            task_stack.add_named(task_completed_image, TaskState.COMPLETED.value)

            # Add the task stack to the list so we can manipulate it later...
            self._task_stack_list.append(task_stack)

            # Create the description label...
            task_label = Gtk.Label(label=task_list[task_index])
            task_label.set_halign(Gtk.Align.START)
            task_label.set_hexpand(True)
            task_list_sizer.attach(task_label, 1, task_index, 1, 1)

        # List of match bundles. First in the list will be the current song and
        #  its matches...
        self._match_bundle_queue = queue.Queue()

    # Fetch assets for the given search key song reference, or a random one if
    #  none provided, and also retrieve its matches...
    def fetch_assets(self, search_key_reference: str=None):

        # Spawn fetch assets thread...
        self._fetch_assets_thread = threading.Thread(target=self.fetch_assets_thread_entry)
        self._fetch_assets_thread.start()

    # Entry point for fetch assets thread...
    def fetch_assets_thread_entry(self):

        # Try to do everything that you need to do...
        try:

            # Reset user interface state...
            GLib.idle_add(self.reset)

            # Disable end session action...
            GLib.idle_add(self._application_window._end_session_action.set_enabled, False)

            # If there any other bundles already cached, remove the current
            #  one...
            if self._match_bundle_queue.qsize() > 0:

                # Remove the most current one...
                match_bundle = self._match_bundle_queue.get()

                # Notify queue the enqueued task is complete...
                self._match_bundle_queue.task_done()

                # Clean up the old one's assets on disk before we add a new
                #  one...
                match_bundle.cleanup()

            # Inform user what we're doing...
            GLib.idle_add(self._application_window.set_status, _('Preparing new match bundle...'))

            # Construct a match bundle and all its paths...
            match_bundle = MatchBundle(total_matches=self._total_matches)

            # Start by telling the user what we're doing...
            GLib.idle_add(self._application_window.set_status, _('Selecting a search key...'))
            self.set_task_state(TaskList.SELECT_SEARCH_KEY, TaskState.IN_PROGRESS)

            # Get the client...
            client = self._application._client

            # Retrieve and save the random song...
            search_key_song_object = client.get_random_song()
#            search_key_song_object = client.get_song(song_reference='MAGNATUNE_05_LE_SOUVENIR_DE_VOUS_ME_TUE_ROBERT_MORTON_ASTERIA_MP3')
            match_bundle.set_search_key_song_object(search_key_song_object)

            # Show task completed...
            self.set_task_state(TaskList.SELECT_SEARCH_KEY, TaskState.COMPLETED)

            # Escape the search key's artist and title in case they contain
            #  characters that might break markup...
            title = html.escape(search_key_song_object.title)
            artist = html.escape(search_key_song_object.artist)

            # Set the search key title label...
            GLib.idle_add(self._search_key_title_label.set_label, title)

            # Set the search key artist label...
            GLib.idle_add(self._search_key_artist_label.set_markup, F'<i>{artist}</i>')

            # Tell user what we're attempting to do next...
            GLib.idle_add(self._application_window.set_status, _('Retrieving search key artwork...'))
            self.set_task_state(TaskList.RETRIEVE_SEARCH_KEY_ARTWORK, TaskState.IN_PROGRESS)

            # Retrieve the search key artwork...
            content, mime = client.get_song_artwork(
                song_reference=search_key_song_object.reference,
                maximum_height=500,
                maximum_width=500)

            # Save search key artwork...
            match_bundle.set_search_key_artwork(content)

            # Show task completed...
            self.set_task_state(TaskList.RETRIEVE_SEARCH_KEY_ARTWORK, TaskState.COMPLETED)

            # Set the search key artwork widget...
            artwork_pixel_buffer = image_data_to_pixbuf(match_bundle.get_search_key_artwork())
            self._search_key_art.set_from_pixbuf(artwork_pixel_buffer)

            # Tell user what we're attempting to do next...
            GLib.idle_add(self._application_window.set_status, _('Performing similarity search...'))
            self.set_task_state(TaskList.PERFORM_SIMILARITY_SEARCH, TaskState.IN_PROGRESS)

            # Prepare search parameters...
            similarity_search_dict = {
                'similar_reference' : search_key_song_object.reference,
                'maximum_results' : self._total_matches
            }

            # Perform similarity search...
            match_object_list = client.get_similar_songs(similarity_search_dict)

            # Show task completed...
            self.set_task_state(TaskList.PERFORM_SIMILARITY_SEARCH, TaskState.COMPLETED)

            # Save each match song object in the bundle...
            for match_index, match_object in enumerate(match_object_list):
                match_bundle.set_match_song_object(match_index, match_object)

            # Tell user what we're attempting to do next...
            GLib.idle_add(self._application_window.set_status, _('Retrieving search key audio...'))
            self.set_task_state(TaskList.RETRIEVE_SEARCH_KEY_AUDIO, TaskState.IN_PROGRESS)

            # Make progress bar visible...
            GLib.idle_add(self._application_window.set_progress_visible, True)

            # Retrieve search key audio...
            client.get_song_download(
                song_reference=search_key_song_object.reference,
                output=match_bundle.get_search_key_path(),
                progress_callback=self.on_progress_callback)

            # Show task completed...
            self.set_task_state(TaskList.RETRIEVE_SEARCH_KEY_AUDIO, TaskState.COMPLETED)

            # Show retrieving artwork task as in progress...
            self.set_task_state(TaskList.RETRIEVE_ARTWORK_FOR_MATCHES, TaskState.IN_PROGRESS)

            # Retrieve each match's cover artwork...
            for index in range(0, self._total_matches):

                # Tell user we are downloading artwork...
                GLib.idle_add(self._application_window.set_status, _(F'Retrieving artwork for match {index+1} of {self._total_matches}...'))

                # Retrieve the match's artwork...
                content, mime = client.get_song_artwork(
                    song_reference=match_object_list[index].reference,
                    maximum_height=500,
                    maximum_width=500)

                # Save search key artwork...
                match_bundle.set_match_artwork(index, content)

                # Move progress bar...
                GLib.idle_add(self._application_window.set_progress, (index + 1) / self._total_matches)

            # Show task completed...
            self.set_task_state(TaskList.RETRIEVE_ARTWORK_FOR_MATCHES, TaskState.COMPLETED)

            # Tell user what we're attempting to do next...
            GLib.idle_add(self._application_window.set_status, _('Retrieving audio for matches...'))
            self.set_task_state(TaskList.RETRIEVE_AUDIO_FOR_MATCHES, TaskState.IN_PROGRESS)

            # Retrieve each match's audio...
            for index in range(0, self._total_matches):

                # Tell user what we're attempting to do next...
                GLib.idle_add(self._application_window.set_status, _(F'Retrieving audio for match {index + 1} of {self._total_matches}...'))

                # Retrieve match's audio...
                client.get_song_download(
                    song_reference=match_object_list[index].reference,
                    output=match_bundle.get_match_path(index),
                    progress_callback=self.on_progress_callback)

            # Show task completed...
            self.set_task_state(TaskList.RETRIEVE_AUDIO_FOR_MATCHES, TaskState.COMPLETED)

            # Add the match bundle to our queue...
            self._match_bundle_queue.put(match_bundle)

            # Tell user what we're attempting to do next...
            GLib.idle_add(self._application_window.set_status, _(F'Accumulated {self._application._training_session.get_total_examples()} data points thus far. Keep going!'))

            # Load the current match bundle...
            GLib.idle_add(self._application_window._match_tuner_page.load_match_bundle)

            # Switch to match tuner page...
            GLib.idle_add(self._application_window._stack.set_visible_child_name, 'MatchTuner')

            # Enable end session action if there's some training data collected...
            if self._application._training_session.get_total_examples() > 0:
                GLib.idle_add(self._application_window._end_session_action.set_enabled, True)

        # Something went wrong...
        except Exception as some_exception:

            # Create an alert dialog...
            alert_dialog = Gtk.AlertDialog()
            alert_dialog.set_message(_('Error'))
            alert_dialog.set_detail(_(F'A problem occurred while retrieving assets. I can either try again or exit from the session after saving it:\n\n{str(some_exception)}'))
            alert_dialog.set_buttons([_('Exit'), _('Retry')])
            alert_dialog.set_default_button(1)
            alert_dialog.set_modal(True)

            # Show it...
            GLib.idle_add(alert_dialog.choose, self._application_window, None, self.on_alert_dialog_callback, None)

        # Regardless of what happens...
        finally:

            # Reset progress and hide progress bar...
            GLib.idle_add(self._application_window.set_progress, 0)
            GLib.idle_add(self._application_window.set_progress_visible, False)

    # Callback for alert dialog...
    def on_alert_dialog_callback(self, alert_dialog, async_result, _):

        # Get the user's selection...
        selection = alert_dialog.choose_finish(async_result)

        # User requested to exit...
        if selection == 0:

            # Save user session...
            self._application._training_session.save()

            # Quit...
            self._application.quit()

        # Otherwise user requested to retry, so do it...
        else:
            self.fetch_assets()

    # Some portion of an asset has been downloaded...
    def on_progress_callback(self, current_size: int, total_size: int):

        # Update progress bar...
        GLib.idle_add(self._application_window.set_progress, current_size / total_size)

    # Reset user interface to fresh state...
    def reset(self):

        # Reset search key artist and title labels...
        self._search_key_artist_label.set_label('')
        self._search_key_title_label.set_label('')

        # Reset search key artwork image...
        self._search_key_art.set_from_icon_name('image-loading')

        # Reset every task to not started...
        for task in TaskList:
            self.set_task_state(task, TaskState.NOT_STARTED)

    # Set a task to a given state in the user interface...
    def set_task_state(self, task: TaskList, state: TaskState):
        GLib.idle_add(self._task_stack_list[task.value].set_visible_child_name, state.value)

