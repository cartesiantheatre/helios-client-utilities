#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2024 Cartesian Theatre. All rights reserved.
#

# System imports...
import html
import sys
import threading

# Gtk related imports...
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gio, Gtk, GLib, GdkPixbuf, Gst, Gdk, GObject, Pango

# Helios...
import helios
from helios_client_utilities.trainer import *

# i18n...
import gettext
_ = gettext.gettext

# Match tuner page class...
class MatchTunerPage(StackPage):

    # Constructor...
    def __init__(self, application_window):

        # Initialize base class...
        super().__init__(application_window, name='MatchTuner', title=_('Match Tuner'))

        # Store reference to application window...
        self._application_window = application_window

        # Store reference to asset loader page...
        self._asset_loader_page = application_window._asset_loader_page

        # Construct master sizer...
        self._sizer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        self._sizer.set_vexpand(True)
        self._sizer.set_hexpand(True)
        self._sizer.set_valign(Gtk.Align.FILL)
        self._sizer.set_halign(Gtk.Align.FILL)
        self._sizer.set_margin_start(10)
        self._sizer.set_margin_end(10)
        self._sizer.set_spacing(10)

        # Construct search key sizer...
        search_key_sizer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        search_key_sizer.set_vexpand(True)
        search_key_sizer.set_valign(Gtk.Align.CENTER)
        self._sizer.append(search_key_sizer)

        # Create search key artwork frame...
        search_key_image_frame = Gtk.Frame()
        search_key_image_frame.set_valign(Gtk.Align.CENTER)
        search_key_image_frame.set_halign(Gtk.Align.CENTER)

        # Event controller for user clicking on search key artwork...
        search_key_gesture_released = Gtk.GestureClick()
        search_key_gesture_released.connect('released', self.on_helios_search_key_released)
        search_key_image_frame.add_controller(search_key_gesture_released)

        # Create search key artwork image...
        self._search_key_image = Gtk.Image.new_from_icon_name('image-loading')
        self._search_key_image.set_icon_size(Gtk.IconSize.LARGE)
        self._search_key_image.set_size_request(300, 300)
        self._search_key_image.set_valign(Gtk.Align.CENTER)
        self._search_key_image.set_halign(Gtk.Align.CENTER)
        search_key_image_frame.set_child(self._search_key_image)
        search_key_sizer.append(search_key_image_frame)

        # Create search key artist and title label...
        self._search_key_artist_and_title_label = Gtk.Label(label=_('Title\n<i><small>Artist</small></i>'))
        self._search_key_artist_and_title_label.set_use_markup(True)
        self._search_key_artist_and_title_label.set_halign(Gtk.Align.CENTER)
        self._search_key_artist_and_title_label.set_justify(Gtk.Justification.CENTER)
        self._search_key_artist_and_title_label.set_wrap(True)
        search_key_sizer.append(self._search_key_artist_and_title_label)

        # Create playback sizer...
        playback_sizer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        search_key_sizer.append(playback_sizer)

        # Note: Song playback was previously managed via Gtk.MediaControls, but
        #  found it to be unreliable with Gtk 4.14. The seek bar does not always
        #  appear. There also appears to be a possible race condition in playing
        #  two songs at the same time without the first one being stopped.
        #  <https://lists.freedesktop.org/archives/gstreamer-devel/2024-July/082073.html>

        # Create play button...
        self._play_button = Gtk.Button.new_from_icon_name('media-playback-start')
        self._play_button.set_sensitive(False)
        self._play_button.connect('clicked', self.on_play_button)
        playback_sizer.append(self._play_button)

        # Create stop button...
        self._stop_button = Gtk.Button.new_from_icon_name('media-playback-stop')
        self._stop_button.set_sensitive(False)
        self._stop_button.connect('clicked', self.on_stop_button)
        playback_sizer.append(self._stop_button)

        # Create a seek slider...
        self._slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 0.5)
        self._slider.set_size_request(300, 20)
        self._slider_handler_id = self._slider.connect('value-changed', self.on_slider_seek)
        playback_sizer.append(self._slider)

        # Create a seek time label...
        self._seek_label = Gtk.Label(label='00:00 / 00:00')
        playback_sizer.append(self._seek_label)

        # Create playback artist / title label...
        self._playback_artist_and_title = Gtk.Label(label=_('<i>Click a song to play.</i>'))
        self._playback_artist_and_title.set_wrap(True)
        self._playback_artist_and_title.set_use_markup(True)
        search_key_sizer.append(self._playback_artist_and_title)

        # Create sizer for buttons...
        button_sizer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_sizer.set_halign(Gtk.Align.CENTER)
        search_key_sizer.append(button_sizer)

        # Create revert button...
        self._revert_button = Gtk.Button()
        sizer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._revert_button.set_child(sizer)
        self._revert_button.connect('clicked', self.on_revert_button)
        revert_button_image = Gtk.Image.new_from_icon_name('document-revert')
        revert_button_image.set_icon_size(Gtk.IconSize.LARGE)
        revert_button_label = Gtk.Label(label=_('Revert'))
        sizer.append(revert_button_image)
        sizer.append(revert_button_label)
        button_sizer.append(self._revert_button)

        # Create skip button...
        skip_button = Gtk.Button()
        sizer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        skip_button.set_child(sizer)
        skip_button.connect('clicked', self.on_skip_button)
        skip_button_image = Gtk.Image.new_from_icon_name('go-jump')
        skip_button_image.set_icon_size(Gtk.IconSize.LARGE)
        skip_button_label = Gtk.Label(label=_('Skip'))
        sizer.append(skip_button_image)
        sizer.append(skip_button_label)
        button_sizer.append(skip_button)

        # Create save button...
        self._save_button = Gtk.Button()
        sizer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._save_button.set_child(sizer)
        self._save_button.set_sensitive(False)
        self._save_button.connect('clicked', self.on_save_button)
        save_button_image = Gtk.Image.new_from_icon_name('go-next')
        save_button_image.set_icon_size(Gtk.IconSize.LARGE)
        save_button_label = Gtk.Label(label=_('Save'))
        sizer.append(save_button_image)
        sizer.append(save_button_label)
        button_sizer.append(self._save_button)

        # Scrolled window to contain Helios and user rankings...
        scrolled_window = Gtk.ScrolledWindow.new()
        scrolled_window.set_overlay_scrolling(False)
        self._sizer.append(scrolled_window)

        # TODO: Split the scrolled window into two, one for system and the other
        #       for user rankings.

        # Construct a horizontal master sizer that the scrolled window will
        #  contain all widgets within...
        scrolled_sizer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        scrolled_window.set_child(scrolled_sizer)

        # Construct Helios ranking sizer...
        helios_ranking_sizer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        helios_ranking_sizer.set_hexpand(True)
        helios_ranking_sizer.set_valign(Gtk.Align.CENTER)
        helios_ranking_sizer.set_halign(Gtk.Align.FILL)
        scrolled_sizer.append(helios_ranking_sizer)

        # List that will contain each Helios match's artwork and artist / title
        #  widgets...
        self._helios_ranking_artwork_image_list = []
        self._helios_ranking_artist_title_label_list = []

        # Create each of the Helios ranking matches...
        for index in range(0, self._asset_loader_page._total_matches):

            # Create parent frame...
            frame = Gtk.Frame()
            frame.frame_ordinal = index
            helios_ranking_sizer.append(frame)

            # Add a sizer to it...
            frame_child_sizer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
            frame_child_sizer.set_margin_start(20)
            frame_child_sizer.set_margin_end(20)
            frame.set_child(frame_child_sizer)

            # Ordinal label...
            ordinal_label = Gtk.Label(label=F'<b>{index + 1}</b>')
            ordinal_label.set_use_markup(True)
            frame_child_sizer.append(ordinal_label)

            # Artwork...
            match_image = Gtk.Image.new_from_icon_name('image-loading')
            match_image.set_icon_size(Gtk.IconSize.LARGE)
            match_image.set_size_request(100, 100)
            match_image.set_margin_start(10)
            match_image.set_margin_top(15)
            match_image.set_margin_bottom(15)
            match_image.set_margin_end(10)
            frame_child_sizer.append(match_image)
            self._helios_ranking_artwork_image_list.append(match_image)

            # Artist and title...
            artist_title_label = Gtk.Label(label='Title\n\n<i><small>Artist</small></i>')
            artist_title_label.set_use_markup(True)
            artist_title_label.set_ellipsize(Pango.EllipsizeMode.END)
            self._helios_ranking_artist_title_label_list.append(artist_title_label)
            frame_child_sizer.append(artist_title_label)

            # Event controller for user clicking on a Helios ranked match to
            #  play song...
            match_gesture_click = Gtk.GestureClick()
            match_gesture_click.connect('released', self.on_helios_ranked_match_primary_released)
            frame.add_controller(match_gesture_click)

            # Drag source for user to start dragging a Helios ranked match...
            helios_match_drag_source = Gtk.DragSource.new()
            helios_match_drag_source.set_actions(Gdk.DragAction.COPY)
            helios_match_drag_source.connect('prepare', self.on_helios_ranked_match_drag_prepare)
            helios_match_drag_source.connect('drag-begin', self.on_match_drag_begin)
            frame.add_controller(helios_match_drag_source)

        # Construct user ranking sizer...
        user_ranking_sizer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        #user_ranking_sizer.set_vexpand(True)
        user_ranking_sizer.set_hexpand(True)
        user_ranking_sizer.set_valign(Gtk.Align.CENTER)
        user_ranking_sizer.set_halign(Gtk.Align.FILL)
        scrolled_sizer.append(user_ranking_sizer)

        # List that will contain each user match's frame widgets, artwork, and
        #  artist / title labels...
        self._user_ranking_frame_list = []
        self._user_ranking_artwork_image_list = []
        self._user_ranking_artist_title_label_list = []

        # Create each of the user ranking matches...
        for index in range(0, self._asset_loader_page._total_matches):

            # Create parent frame...
            frame = Gtk.Frame()
            frame.frame_ordinal = index
            self._user_ranking_frame_list.append(frame)
            user_ranking_sizer.append(frame)

            # Add a sizer to it...
            frame_child_sizer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
            frame_child_sizer.set_margin_start(20)
            frame_child_sizer.set_margin_end(20)
            frame.set_child(frame_child_sizer)

            # Ordinal label...
            ordinal_label = Gtk.Label(label=F'<b>{index + 1}</b>')
            ordinal_label.set_use_markup(True)
            frame_child_sizer.append(ordinal_label)

#            # Delete button...
#            delete_button = Gtk.Button()
#            sizer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
##            delete_button.connect('clicked', self.on_delete_button)
#            delete_button_image = Gtk.Image.new_from_icon_name('edit-delete')
##            delete_button_image.set_icon_size(Gtk.IconSize.LARGE)
#            delete_button.set_child(delete_button_image)
#            frame_child_sizer.append(delete_button)

            # Artwork...
            match_image = Gtk.Image.new_from_icon_name('starred')
            match_image.set_icon_size(Gtk.IconSize.LARGE)
            match_image.set_size_request(100, 100)
            match_image.set_margin_start(10)
            match_image.set_margin_top(15)
            match_image.set_margin_bottom(15)
            match_image.set_margin_end(10)
            self._user_ranking_artwork_image_list.append(match_image)
            frame_child_sizer.append(match_image)

            # Artist and title...
            artist_title_label = Gtk.Label()#label='Title\n<i><small>Artist</small></i>')
            artist_title_label.set_use_markup(True)
            artist_title_label.set_ellipsize(Pango.EllipsizeMode.END)
            self._user_ranking_artist_title_label_list.append(artist_title_label)
            frame_child_sizer.append(artist_title_label)

            # Event controller for user clicking on a Helios ranked match to
            #  play song...
            match_gesture_click = Gtk.GestureClick()
            match_gesture_click.connect('released', self.on_user_ranked_match_primary_released)
            frame.add_controller(match_gesture_click)

            # Event controller for user secondary mouse on Helios ranked match
            #  to open popup menu...
            match_gesture_single_click = Gtk.GestureSingle()
            match_gesture_single_click.set_button(3)
            match_gesture_single_click.connect('begin', self.on_user_ranked_match_secondary_begin)
            frame.add_controller(match_gesture_single_click)

            # Drag source for user to start dragging a user ranked match...
            user_match_drag_source = Gtk.DragSource.new()
            user_match_drag_source.set_actions(Gdk.DragAction.COPY)
            user_match_drag_source.connect('prepare', self.on_user_ranked_match_drag_prepare)
            user_match_drag_source.connect('drag-begin', self.on_match_drag_begin)
            user_match_drag_source.connect('drag-cancel', self.on_user_ranked_match_drag_cancel)
            frame.add_controller(user_match_drag_source)

            # Drop target for user to drag a Helios or user ranked match to here...
            helios_match_drop_target = Gtk.DropTarget.new(GObject.TYPE_INT, Gdk.DragAction.COPY)
            helios_match_drop_target.connect('drop', self.on_ranked_match_drop)
            helios_match_drop_target.connect('accept', self.on_user_match_accept)
            frame.add_controller(helios_match_drop_target)

        # Location for the loaded match bundle...
        self._match_bundle = None

        # List of Helios match indices loaded in the user matches, or None if
        #  nothing dragged there...
        self._user_ranking_indices = [None] * self._asset_loader_page._total_matches

        # Initialize GStreamer...
        Gst.init(None)

        # Create a playbin element for audio playback...
        self._playbin = Gst.ElementFactory.make("playbin", None)

        # Failed to initialize playbin element...
        if not self._playbin:

            # Log it
            sys.stderr.write('The playbin GStreamer plugin appears to be missing...\n')

            # Exit...
            sys.exit(1)

        # Start an update timer for every quarter of a second...
        GLib.timeout_add(250, self.update_timer_callback)

    # Load the current match bundle...
    def load_match_bundle(self):

        # Get the current match bundle...
        self._match_bundle = self._asset_loader_page._match_bundle_queue.get()

        # Notify queue the enqueued task is complete...
        self._asset_loader_page._match_bundle_queue.task_done()

        # Set search key artwork...
        artwork_pixel_buffer = image_data_to_pixbuf(self._match_bundle.get_search_key_artwork())
        self._search_key_image.set_from_pixbuf(artwork_pixel_buffer)

        # Get the search key song object...
        search_key_song_object = self._match_bundle.get_search_key_song_object()

        # Escape the artist and title in case they contain characters that might
        #  break markup...
        artist = html.escape(search_key_song_object.artist)
        title = html.escape(search_key_song_object.title)

        # Set artist and title...
        self._search_key_artist_and_title_label.set_label(F'{title}\n<i><small>{artist}</small></i>')

        # Load each Helios match...
        for match_index in range(0, self._asset_loader_page._total_matches):

            # Get artwork widget...
            artwork_image = self._helios_ranking_artwork_image_list[match_index]

            # Set artwork...
            artwork_pixel_buffer = image_data_to_pixbuf(self._match_bundle.get_match_artwork(match_index))
            artwork_image.set_from_pixbuf(artwork_pixel_buffer)

            # Get match object...
            match_object = self._match_bundle.get_match_song_object(match_index)

            # Get artist / title label...
            artist_title_label = self._helios_ranking_artist_title_label_list[match_index]

            # Escape the artist and title in case they contain characters that
            #  might break markup...
            artist = html.escape(match_object.artist)
            title = html.escape(match_object.title)

            # Set artist / title label...
            artist_title_label.set_label(F'{title}\n\n<i><small>{artist}</small></i>')

    # Drag source: User about to beging dragging a Helios ranked match...
    def on_helios_ranked_match_drag_prepare(self, drag_source, x_coordinate, y_coordinate):

        # Get frame containing the Helios ranked match...
        frame = drag_source.get_widget()

        # Provide the drop target with the Helios match ordinal...
        match_ordinal = frame.frame_ordinal

        # Construct a content provider that stores the above and return it...
        return Gdk.ContentProvider.new_for_value(
            GObject.Value(GObject.TYPE_INT, match_ordinal))

    # User released primary mouse on a Helios ranked match...
    def on_helios_ranked_match_primary_released(self, gesture_click, number_of_press, x_coordinate, y_coordinate):

        # Get the widget mouse button was released on...
        widget = gesture_click.get_widget()

        # Make sure release was inside the widget...
        if not widget.contains(x_coordinate, y_coordinate):
            return

        # Get the Helios ranked match ordinal...
        match_ordinal = widget.frame_ordinal

        # Get the song object for match...
        song_object = self._match_bundle.get_match_song_object(match_ordinal)

        # Get the path to the song...
        path = self._match_bundle.get_match_path(match_ordinal)

        # Start playing the match...
        self.play_song(song_object, path, F'<i>Ranked match #{match_ordinal + 1}</i>')

    # Play button clicked...
    def on_play_button(self, button):

        # Get playback state...
        state = self._playbin.get_state(Gst.CLOCK_TIME_NONE)

        # Song is currently playing, so pause it...
        if state.state is Gst.State.PLAYING:
            self._playbin.set_state(Gst.State.PAUSED)

        # Song is currently paused, so resume playing...
        elif state.state is Gst.State.PAUSED:
            self._playbin.set_state(Gst.State.PLAYING)

    # Drop target: User dropped a Helios or user ranked match over a drag target
    #  user ranking slot...
    def on_ranked_match_drop(self, drop_target, gvalue, x_coordinate, y_coordinate):

        # Get frame containing the user ranked match...
        frame = drop_target.get_widget()

        # Make sure release was inside the frame. If it wasn't, don't accept the
        #  drop...
        if not frame.contains(x_coordinate, y_coordinate):
            return False

        # Get the Helios and user match indices...
        source_helios_match_index = int(gvalue)
        destination_user_match_index = frame.frame_ordinal

        # Check if this Helios match was already among the user rankings...
        for index in range(0, self._asset_loader_page._total_matches):
            if self._user_ranking_indices[index] is source_helios_match_index:
                self._user_ranking_indices[index] = None

        # Load source match index into the destination...
        self._user_ranking_indices[destination_user_match_index] = source_helios_match_index

        # Reload user interface for user matches...
        self.refresh_user_interface()

        # Accept the drop...
        return True

    # Drag source: User about to begin dragging a user ranked match...
    def on_user_ranked_match_drag_prepare(self, drag_source, x_coordinate, y_coordinate):

        # Get frame containing the Helios ranked match...
        frame = drag_source.get_widget()

        # Provide the drop target with the Helios match ordinal...
        match_ordinal = self._user_ranking_indices[frame.frame_ordinal]

        # Nothing in this location...
        if match_ordinal is None:
            return None

        # Construct a content provider and return it...
        return Gdk.ContentProvider.new_for_value(
            GObject.Value(GObject.TYPE_INT, match_ordinal))

    # Drag source: User has cancelled dragging a user ranked match...
    def on_user_ranked_match_drag_cancel(self, drag_source, drag_object, drag_cancel_reason):

        # Only interested if user released over a non-existent drop target...
        if drag_cancel_reason is not Gdk.DragCancelReason.NO_TARGET:
            return False

        # Get the source frame...
        frame = drag_source.get_widget()

        # Remove the match from the user match slot...
        self._user_ranking_indices[frame.frame_ordinal] = None

        # Reload user interface...
        self.refresh_user_interface()

        # Signal that we handled the cancel operation...
        return True

    # User released primary mouse on a user ranked match...
    def on_user_ranked_match_primary_released(self, gesture_click, number_of_press, x_coordinate, y_coordinate):

        # Get the widget mouse button was released on...
        widget = gesture_click.get_widget()

        # Make sure release was inside the widget...
        if not widget.contains(x_coordinate, y_coordinate):
            return

        # Get the user ranked match ordinal...
        match_ordinal = self._user_ranking_indices[widget.frame_ordinal]

        # Nothing was loaded in this slot...
        if match_ordinal is None:

            # Unload any media stream...
            self.stop_playback()

            # Clear artist / title label...
            self._playback_artist_and_title.set_markup(_('<i>Click a song to play.</i>'))

            # Don't try to play anything else...
            return

        # Get the song object for match...
        song_object = self._match_bundle.get_match_song_object(match_ordinal)

        # Get the path to the song...
        path = self._match_bundle.get_match_path(match_ordinal)

        # Start playing the match...
        self.play_song(song_object, path, _(F'<i>User match #{widget.frame_ordinal + 1}</i>'))

    # User released secondary mouse on a user ranked match...
    def on_user_ranked_match_secondary_begin(self, gesture_single, event_sequence):

        # Get the frame widget...
        widget = gesture_single.get_widget()

        # Get the user ranked match ordinal...
        match_ordinal = self._user_ranking_indices[widget.frame_ordinal]

        # Nothing was loaded in this slot, so ignore it...
        if match_ordinal is None:
            return

        # Get mouse location on frame widget...
        _, x_coordinate, y_coordinate = gesture_single.get_point()

        # Create menu...
#        menu = Gio.Menu.new()
#        menu.append('Remove')

#        widget.popover = Gtk.PopoverMenu()
#        widget.popover.set_menu_model(menu)
#        widget.popover.popup()

    # User released mouse on search key area...
    def on_helios_search_key_released(self, gesture_click, number_of_press, x_coordinate, y_coordinate):

        # Get the widget mouse button was released on...
        widget = gesture_click.get_widget()

        # Make sure release was inside the widget...
        if not widget.contains(x_coordinate, y_coordinate):
            return

        # Get the song object for the search key...
        song_object = self._match_bundle.get_search_key_song_object()

        # Get the path to the song...
        path = self._match_bundle.get_search_key_path()

        # Start playing the match...
        self.play_song(song_object, path, F'<i>Search key</i>')

    # Drag source: User has begun dragging either a Helios or user ranked
    #  match...
    def on_match_drag_begin(self, drag_source, data):

        # Get frame containing the Helios ranked match...
        frame = drag_source.get_widget()

        # Get a screenshot of the frame...
        paintable = Gtk.WidgetPaintable.new(frame)

        # Set the screenshot as the cursor icon so that the frame and its
        #  contents are what appears to be dragged...
        drag_source.set_icon(paintable, 0, 0)

    # Revert button clicked...
    def on_revert_button(self, button):

        # List of user matches should be all none...
        self._user_ranking_indices = [None] * self._asset_loader_page._total_matches

        # Reload user interface for user matches...
        self.refresh_user_interface()

    # Skip button clicked...
    def on_skip_button(self, button):

        # Reset user interface...
        self.reset()

        # Switch back to asset loader page...
        self._application_window._stack.set_visible_child_name('AssetLoader')

        # Trigger a fresh asset bundle retrieval...
        self._application_window._asset_loader_page.fetch_assets()

    # Drop target: User dragged a Helios ranked match over a user match slot...
    def on_user_match_accept(self, drop_target, user_data):

        # Accept the drop...
        return True

    # Save button clicked...
    def on_save_button(self, button):

        # Create an alert dialog...
        alert_dialog = Gtk.AlertDialog()
        alert_dialog.set_message(_('Save?'))
        alert_dialog.set_detail(_(F'Are you ready to add this training data into your session? This cannot be undone.'))
        alert_dialog.set_buttons([_('Cancel'), _('Save')])
        alert_dialog.set_default_button(0)
        alert_dialog.set_modal(True)

        # Show dialog...
        alert_dialog.choose(self._application_window, None, self.on_save_confirm_dialog_callback, None)

    # Save confirm dialog callback...
    def on_save_confirm_dialog_callback(self, alert_dialog, async_result, _):

        # Get the user's selection...
        selection = alert_dialog.choose_finish(async_result)

        # User requested to cancel...
        if selection == 0:
            return

        # Otherwise spawn triplet mining thread...
        self._triplet_mining_thread = threading.Thread(target=self.triplet_mining_thread_entry)
        self._triplet_mining_thread.start()

    # The user is trying to seek...
    def on_slider_seek(self, slider):

        # Get the new requested time...
        seek_time_seconds = self._slider.get_value()

        # Tell playbin to seek in stream...
        self._playbin.seek_simple(
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            seek_time_seconds * Gst.SECOND)

    # Stop button clicked...
    def on_stop_button(self, button):

        # Stop playback...
        self.stop_playback()

    # Play the requested song at the given path...
    def play_song(self, song_object, path, label_markup):

        # Stop any other song that might have been playing...
        self.stop_playback()

        # Unload any other song that might have been loaded...
        self._playbin.set_state(Gst.State.NULL)

        # Set artist / title label...
        self._playback_artist_and_title.set_markup(label_markup)

        # Create a URI to the media file to play...
        media_file_uri = Gst.filename_to_uri(path)

        # Load the media file...
        self._playbin.set_property('uri', media_file_uri)

#        # Check if there was an error...
#        if media_file.get_error() is not None:

#            # Show an error message...
#            alert_dialog = Gtk.AlertDialog()
#            alert_dialog.set_message(_('Error'))
#            alert_dialog.set_detail(media_file.get_error().message)
#            alert_dialog.set_modal(True)
#            alert_dialog.show()

#            # Do nothing else...
#            return

        # Begin playback...
        self._playbin.set_state(Gst.State.PLAYING)

    # Reload user interface...
    def refresh_user_interface(self):

        # Enable the save button, but only if the user has assigned at least
        #  one ranked user match. Otherwise nothing to save...
        self._save_button.set_sensitive(
            any(element is not None for element in self._user_ranking_indices))

        # Update each user match frame...
        for user_match_frame_index in range(0, self._asset_loader_page._total_matches):

            # Get user match's frame widget...
            user_match_frame = self._user_ranking_frame_list[user_match_frame_index]

            # Which Helios match index is assigned to this frame?
            helios_match_index = self._user_ranking_indices[user_match_frame_index]

            #print(F'self._user_ranking_indices[{user_match_frame_index}]={helios_match_index}')

            # No match assigned here, reset it...
            if helios_match_index is None:

                # Reset artwork to star icon...
                artwork_image = self._user_ranking_artwork_image_list[user_match_frame_index]
                artwork_image.set_from_icon_name('starred')
                artwork_image.set_icon_size(Gtk.IconSize.LARGE)

                # Clear artist / title label...
                artist_title_label = self._user_ranking_artist_title_label_list[user_match_frame_index]
                artist_title_label.set_label('')

            # Otherwise a Helios match was assigned to this frame...
            else:

                # Get artwork widget...
                artwork_image = self._user_ranking_artwork_image_list[user_match_frame_index]

                # Load and artwork...
                artwork_pixel_buffer = image_data_to_pixbuf(self._match_bundle.get_match_artwork(helios_match_index))
                artwork_image.set_from_pixbuf(artwork_pixel_buffer)

                # Get match object...
                match_object = self._match_bundle.get_match_song_object(helios_match_index)

                # Set artist / title label...
                artist_title_label = self._user_ranking_artist_title_label_list[user_match_frame_index]

                # Escape the artist and title in case they contain characters that
                #  might break markup...
                artist = html.escape(match_object.artist)
                title = html.escape(match_object.title)

                # Set artist / title label...
                artist_title_label.set_label(F'{title}\n\n<i><small>{artist}</small></i>')

    # Reset user interface...
    def reset(self):

        # Revert user match list to nothing...
        self._revert_button.emit('clicked')

        # Cleanup the current bundle via its destructor, if bundle loaded...
        self._match_bundle = None

        # Unload any media stream...
        self.stop_playback()

        # Clear artist / title label...
        self._playback_artist_and_title.set_markup(_('<i>Click a song to play.</i>'))

    # Stop playback...
    def stop_playback(self):

        # Pause the stream...
        self._playbin.set_state(Gst.State.PAUSED)

        # Move seek slider back to the beginning. This will also have the effect
        #  of calling on_slider_seek() which will reset the playback position in
        #  the actual stream...
        self._slider.set_value(0)

    # Entry point for user training session upload thread...
    def triplet_mining_thread_entry(self):

        # Disable user interface...
        GLib.idle_add(self._sizer.set_sensitive, False)

        # Storage for list of learning example triplets...
        new_learning_examples = []

        # Get search reference...
        search_reference = self._match_bundle.get_search_key_song_object().reference

        # Storage for ordered system generated song reference rankings...
        system_rankings = []

        # Generate an ordered list of the system generated song references...
        for system_ranking_index in range(0, self._asset_loader_page._total_matches):
            song_object = self._match_bundle.get_match_song_object(system_ranking_index)
            system_rankings.append(song_object.reference)

        # Storage for an ordered user generated song reference rankings...
        user_rankings = []

        # Remove all of the empty (None) slots from the user ranking indices...
        coalesced_user_ranking_indices = list(filter(lambda a: a != None, self._user_ranking_indices))

        # Generate an ordered list of the user generated song reference
        #  rankings...
        for system_ranking_index in coalesced_user_ranking_indices:
            song_object = self._match_bundle.get_match_song_object(system_ranking_index)
            user_rankings.append(song_object.reference)

        # Try to perform mining on the server...
        try:

            # Remove all of the empty (None) slots from the user ranking indices...
            coalesced_user_ranking_indices = list(filter(lambda a: a != None, self._user_ranking_indices))

            # Inform user of what we're doing...
            GLib.idle_add(self._application_window.set_status, _(F'Asking server to extrapolate new data points. Please wait...'))

            # Request triplet mining of learning examples from server...
            new_learning_examples = self._application._client.perform_triplet_mining(
                search_reference,
                system_rankings,
                user_rankings)

            # Inform user of what we're doing...
            GLib.idle_add(self._application_window.set_status, _(F'Added {len(new_learning_examples)} new data points...'))

            # Get training session...
            training_session = self._application._training_session

            # Add each triplet to user's training session...
            for learning_example in new_learning_examples:

                #print(F'Anchor: {learning_example.anchor}')
                #print(F'Positive: {learning_example.positive}')
                #print(F'Negative: {learning_example.negative}\n')

                # Add triplet to training session...
                training_session.add_example(
                    learning_example.anchor,
                    learning_example.positive,
                    learning_example.negative)

            # Save training session...
            training_session.save()

            # Reset user interface...
            self.reset()

            # Switch back to asset loader page...
            self._application_window._stack.set_visible_child_name('AssetLoader')

            # Trigger a fresh asset bundle retrieval...
            self._application_window._asset_loader_page.fetch_assets()

        # Something went wrong...
        except Exception as some_exception:

            # Show exception in status bar...
            GLib.idle_add(self._application_window.set_status, _(F'Error: {str(some_exception)}'))

        # Regardless of what happens...
        finally:

            # Re-enable user interface...
            GLib.idle_add(self._sizer.set_sensitive, True)

    # User interface update timer callback...
    def update_timer_callback(self):

        # Try to get duration of song...
        duration_success, duration_nanoseconds = self._playbin.query_duration(Gst.Format.TIME)

        # If we were able to get the duration...
        if duration_success:

            # Update seek slider's range...
            self._slider.set_range(0, duration_nanoseconds / Gst.SECOND)

            # Convert duration from nanoseconds to minutes and seconds...
            duration_total_seconds = duration_nanoseconds / 1000000000
            duration_minutes = int(duration_total_seconds / 60)
            duration_seconds = int(duration_total_seconds - (duration_minutes * 60))

        # Try to get the playback position of song...
        position_success, position_nanoseconds = self._playbin.query_position(Gst.Format.TIME)

        # If we were able to obtain the playback position...
        if position_success:

            # Convert playback position from nanoseconds to minutes and seconds...
            position_total_seconds = position_nanoseconds / 1000000000
            position_minutes = int(position_total_seconds / 60)
            position_seconds = int(position_total_seconds - (position_minutes * 60))

            # Move seek bar position, blocking the seek handler so we don't
            #  seek when we set_value()...
            self._slider.handler_block(self._slider_handler_id)
            self._slider.set_value(float(position_nanoseconds) / Gst.SECOND)
            self._slider.handler_unblock(self._slider_handler_id)

        # If we were able to get both the duration of the song and its
        #  current playback position...
        if duration_success and position_success:

            # Update seek label...
            self._seek_label.set_label(F'{position_minutes:02}:{position_seconds:02} / {duration_minutes:02}:{duration_seconds:02}')

        # Get playback state...
        state = self._playbin.get_state(Gst.CLOCK_TIME_NONE)

        # Song is currently playing...
        if state.state is Gst.State.PLAYING:

            # Change play button's icon to a pause icon...
            self._play_button.set_icon_name('media-playback-pause')

            # Enable play, stop, and seek slider...
            self._play_button.set_sensitive(True)
            self._stop_button.set_sensitive(True)
            self._slider.set_sensitive(True)

            # If we were able to get both the duration of the song and its
            #  current playback position...
            if duration_success and position_success:

                # If we reached the end of the song, update UI for stop state.
                #  For some reason GStreamer sometimes reports a position that 
                #  isn't exactly the end when it's reached the end. Sometimes it
                #  is earlier than the end and other times it exceeds it...
                if position_nanoseconds + Gst.SECOND >= duration_nanoseconds:
                    self.stop_playback()

        # Song is paused...
        elif state.state is Gst.State.PAUSED:

            # Change play button's icon to a play icon...
            self._play_button.set_icon_name('media-playback-start')

            # Make seek slider sensitive...
            self._slider.set_sensitive(True)

        # Song is not loaded...
        elif state.state is Gst.State.NULL:

            # Reset seek bar position, blocking the seek handler so we don't
            #  seek when we set_value()...
            self._slider.handler_block(self._slider_handler_id)
            self._slider.set_value(0)
            self._slider.handler_unblock(self._slider_handler_id)

            # Disable play, stop, and seek slider...
            self._play_button.set_sensitive(False)
            self._stop_button.set_sensitive(False)
            self._slider.set_sensitive(False)

            # Reset seek label...
            self._seek_label.set_label('00:00 / 00:00')

        # Don't cancel timer...
        return True

