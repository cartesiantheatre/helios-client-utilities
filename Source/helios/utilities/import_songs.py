#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2019 Cartesian Theatre. All rights reserved.
#

# System imports...
import helios
from helios.utilities.common import add_common_arguments, zeroconf_find_server
from pprint import pprint
from termcolor import colored
import argparse
import attr
import base64
import colorama
import concurrent.futures
import csv
import datetime
import logging
import queue
import simplejson
import sys
from functools import partial
import threading
import time

# i18n...
import gettext
_ = gettext.gettext

# Add arguments specific to this utility to argument parser...
def add_arguments(argument_parser):

    # Define positional argument for catalogue file...
    argument_parser.add_argument(
        'catalogue_file',
        help=_('Path to input catalogue file.'))

    # Define behaviour for --delimiter...
    argument_parser.add_argument(
        '--delimiter',
        default=',',
        dest='delimiter',
        nargs='?',
        help=_('Delimiter character to use. Default is comma character.'))

    # Define behaviour for --max-errors...
    argument_parser.add_argument(
        '--max-errors',
        default=2,
        dest='maximum_errors',
        nargs='?',
        type=int,
        help=_('Maximum number of errors to tolerate before exiting. Defaults to ten.'))

    # Define behaviour for --no-store, defaults store to true...
    argument_parser.add_argument(
        '--no-store',
        action='store_false',
        default=True,
        dest='store',
        help=_('Delete the song on the server immediately after analysis. Defaults to store.'))

    # Define behaviour for --offset...
    argument_parser.add_argument(
        '--offset',
        default=1,
        dest='offset',
        nargs='?',
        type=int,
        help=_('Row offset to begin processing on. Defaults to 1, or first line of file.'))

    # Define behaviour for --max-errors...
    argument_parser.add_argument(
        '--threads',
        default=0,
        dest='threads',
        nargs='?',
        type=int,
        help=_('Number of concurrent imports. Default is the number of logical cores on the server.'))

# Class to batch import a bunch of songs at once. Uses multiple synchronized
#  processes...
class BatchSongImporter(object):

    # Constructor...
    def __init__(self, arguments, songs_total):

        self._arguments             = arguments
        self._errors_remaining      = arguments.maximum_errors
        self._executor              = None
        self._queue                 = queue.Queue(self._arguments.threads) # maxsize=1
        self._songs_processed       = arguments.offset - 1
        self._songs_total           = songs_total
        self._stop_event            = threading.Event()
        self._thread_lock           = threading.Lock()

    def _add_song_consumer_thread(self, consumer_thread_index):

        logging.debug(F'thread {consumer_thread_index}: spawned')

        # Construct a Helios client...
        client = helios.client(
            token=self._arguments.token,
            host=self._arguments.host,
            port=self._arguments.port,
            verbose=self._arguments.verbose)

        # Keep adding songs as long as we haven't been instructed to stop...
        while not self._stop_event.is_set():

            # Try to submit a song...
            try:

                # Retrieve a csv_row, or block for at most one second before
                #  checking to see if bail requested...
                try:
                    logging.debug(F'thread {consumer_thread_index}: Waiting for a job.')
                    csv_row = self._queue.get(timeout=1)
                    reference = csv_row['reference']
                    logging.debug(F'thread {consumer_thread_index}: Got a job {reference}.')
                    with self._thread_lock:
                        self._songs_processed += 1
                        logging.info(F'thread {consumer_thread_index}: {reference} Processing song {self._songs_processed} of {self._songs_total}.')

                except queue.Empty:
                    logging.debug(F'thread {consumer_thread_index}: Job queue empty, will try again.')
                    continue

                # Check if the song already has been added, and if so, skip it...
                try:
                    logging.debug(F'thread {consumer_thread_index}: Checking if {reference} song already exists.')
                    existing_song = client.get_song(song_reference=csv_row['reference'])
                    logging.info(F'thread {consumer_thread_index}: {reference} Song already known to server, skipping.')
                    continue
                except helios.exceptions.NotFound:
                    pass

                logging.info(F"thread {consumer_thread_index}: {reference} Song is new, submitting.")

                # Magic field constant to signal to use autodetection...
                autodetect = '<AUTODETECT>'

                # Construct new song...
                new_song_dict = {

                    'album' : (csv_row['album'], None)[csv_row['album'] == autodetect],
                    'artist' : (csv_row['artist'], None)[csv_row['artist'] == autodetect],
                    'title' : (csv_row['title'], None)[csv_row['title'] == autodetect],
                    'genre' : (csv_row['genre'], None)[csv_row['genre'] == autodetect],
                    'isrc' : (csv_row['isrc'], None)[csv_row['isrc'] == autodetect],
                    'year' : (csv_row['year'], None)[csv_row['year'] == autodetect],
                    'file' : base64.b64encode(open(csv_row['path'], 'rb').read()).decode('ascii'),
                    'reference' : csv_row['reference']
                }

                # Upload...
                stored_song = client.add_song(
                    new_song_dict=new_song_dict,
                    store=self._arguments.store,
                    progress_callback=partial(
                        self._current_song_progress_callback, consumer_thread_index, reference))

                logging.info(_(F'thread {consumer_thread_index}: {reference} Added successfully.'))

            except simplejson.errors.JSONDecodeError as someException:
                logging.info(F'thread {consumer_thread_index}: {reference} JSON decode error: {str(someException)}')
                self.stop()

            # An exception occured...
            except Exception as someException:

                logging.info(F"thread {consumer_thread_index}: {reference} {str(someException)}")# (type {type(someException)})")

                # Update error counter...
                #self._errors_remaining -= 1

                # If maximum error count reached, abort...
                if self._errors_remaining <= 0:

                    # Alert user...
                    logging.info(_(F'Maximum errors reached (set to {self._arguments.maximum_errors}). Aborting.'))

                    # Stop all threads...
                    self.stop()

            # Connection failed...
            except helios.exceptions.Connection as someException:
                logging.info(F"thread {consumer_thread_index}: {reference} {str(someException)}")
                self.stop()

            # In any event, update the total songs progress bar...
            finally:
                self._queue.task_done()

        logging.debug(F'thread {consumer_thread_index}: Exiting.')


    # Progress bar callback...
    def _current_song_progress_callback(
        self, consumer_thread_index, reference, bytes_read, new_bytes, bytes_total):

        # If we're done uploading, update description to analysis stage...
        if bytes_read == bytes_total:
            logging.info(F'thread {consumer_thread_index}: {reference} Awaiting song analysis.')

       # time.sleep(0.001)

    # Start batch import...
    def start(self, csv_reader):

        logging.debug(F'producer: Creating thread pool executor of {self._arguments.threads} threads')

        # Construct consumer thread pool and run it...
        with concurrent.futures.ThreadPoolExecutor() as self._executor:

            try:
                # Spawn consumer threads and hand them a consumer thread index...
                logging.info(F"producer: Will use {self._arguments.threads} threads.")
                for consumer_thread_index in range(1, self._arguments.threads):
                    self._executor.submit(
                        self._add_song_consumer_thread, consumer_thread_index)

                # Create a job, while there are some...
                for current_line_offset, csv_row in enumerate(csv_reader, 1):

                    if current_line_offset < self._arguments.offset:
                        continue

                    logging.debug(F"producer: Read csv row {csv_row['reference']}")

                    # Keep trying to add the job to the work queue until
                    #  successful or we are told to abort...
                    while not self._stop_event.is_set():

                        # Try to add job...
                        try:
                            logging.debug('producer: Waiting to add work to work queue')
                            self._queue.put(csv_row, timeout=1)
                            logging.debug(F"producer: Added row {csv_row['reference']} to work queue")

                        # Queue is full, try again...
                        except queue.Full:
                            logging.debug('producer: Queue full, trying again')
                            continue

                        # Done adding job. Go prepare next job...
                        break

                    if self._stop_event.is_set():
                        break

                # Wait for all current work on the queue to be retrieved from
                #  consumer threads...
                self._queue.join()

            # Parser error, treated as fatal...
            except csv.Error as someException:
                logging.error(F"Syntax error, line {csv_reader.line_num}: {someException}")

            finally:
                logging.debug('producer: Done reading rows')
                self.stop()

    # Gracefully stop all importation processes...
    def stop(self):

        # Signal to all consumer threads to stop...
        logging.debug('Waiting for all pending transactions to complete...')
        self._stop_event.set()

        # Wait for all consumer threads to stop...
        logging.debug('Waiting for executor to shutdown().')
        self._executor.shutdown()
        logging.debug('Executor shutdown() successfully.')

    # Destructor...
    def __del__(self):

        # Stop importation...
        self.stop()

# Main function...
def main():

    # Initialize the argument parser...
    argument_parser = argparse.ArgumentParser(
        description=_('Batch import songs into Helios.'))

    # Add common arguments to argument parser...
    add_common_arguments(argument_parser)

    # Add arguments specific to this utility to argument parser...
    add_arguments(argument_parser)

    # Parse the command line...
    arguments = argument_parser.parse_args()
    arguments.offset = max(arguments.offset, 1)

    # Setup logging...
    format = "%(asctime)s: %(message)s"
    if arguments.verbose:
        logging.basicConfig(format=format, level=logging.DEBUG, datefmt="%H:%M:%S")
    else:
        logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")

    # Initialize terminal colour...
    colorama.init()

    # Success flag to determine exit code...
    success = False

    # Total number of songs in the input catalogue file...
    songs_total = 0

    # Prepare column fieldnames from CSV input catalogue...
    fieldnames = [
        'reference',
        'album',
        'artist',
        'title',
        'genre',
        'isrc',
        'year',
        'path'
    ]

    # Batch importer will be constructed within try block...
    batch_importer = None

    # Try to process the catalogue file...
    try:

        # If no host provided, use Zeroconf auto detection...
        if not arguments.host:
            arguments.host = zeroconf_find_server()[0]

        # Create a client...
        client = helios.client(
            token=arguments.token,
            host=arguments.host,
            port=arguments.port,
            verbose=arguments.verbose)

        # Count the number of songs in the input catalogue...
        with open(arguments.catalogue_file, 'r') as catalogue_file:
            for line in catalogue_file:
                if line.strip():
                    songs_total += 1

        # Verify we can reach the server...
        server_status = client.get_server_status()

        # If user requested to autodetect the number of threads, set to the
        #  number of logical cores on the server...
        if arguments.threads == 0:
            arguments.threads = server_status.cpu.cores

        # Initialize batch song importer...
        batch_importer = BatchSongImporter(arguments, songs_total)

        # Open catalogue file again, but this time for parsing. Set newline
        #  empty per <https://docs.python.org/3/library/csv.html#id3>
        catalogue_file = open(arguments.catalogue_file, 'r', newline='')

        # Initialize the CSV reader...
        reader = csv.DictReader(
            f=catalogue_file,
            fieldnames=fieldnames,
            delimiter=arguments.delimiter,
            doublequote=False,
            escapechar='\\',
            quoting=csv.QUOTE_MINIMAL,
            skipinitialspace=True,
            strict=True)

        # Submit the songs...
        batch_importer.start(reader)

        # Determine how we will exit...
        success = True #(errors_remaining == arguments.maximum_errors)

    # User trying to abort...
    except KeyboardInterrupt:
        print(_('Aborting, please wait a moment...'))
        success = False

    # Helios exception...
    except helios.exceptions.ExceptionBase as someException:
        print(someException.what())

    # Some other kind of exception...
    except Exception as someException:
        print(_(f"An unknown exception occurred: {str(someException)}"))

    # Cleanup...
    finally:

        # Stop batch import, in case it hasn't already...
        if batch_importer:
            batch_importer.stop()
            del batch_importer

        # Close input catalogue file...
        catalogue_file.close()

    # Exit with status code based on whether we were successful or not...
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

# Entry point...
if __name__ == '__main__':

    # Run main function...
    main()

