#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2021 Cartesian Theatre. All rights reserved.
#

# System imports...
import argparse
import base64
import concurrent.futures
from functools import partial
import logging
import queue
import sys
import threading
import time
import traceback

# Other imports
import helios
from helios.utilities.common import add_common_arguments, zeroconf_find_server
import numpy
import pandas
import simplejson

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

    # Define behaviour for --no-store, defaults store to true...
    argument_parser.add_argument(
        '--dry-run',
        action='store_true',
        default=False,
        dest='dry_run',
        help=_('Perform a dry run only. Do not actually make any modifications '
               'to the server.'))

    # Define behaviour for --maximum-errors...
    argument_parser.add_argument(
        '--maximum-errors',
        default=1,
        dest='maximum_errors',
        nargs='?',
        type=int,
        help=_('Maximum number of errors to tolerate before exiting. Defaults '
               'to one. Set to zero for unlimited non-fatal.'))

    # Define behaviour for --no-store, defaults store to true...
    argument_parser.add_argument(
        '--no-store',
        action='store_false',
        default=True,
        dest='store',
        help=_('Delete the song on the server immediately after analysis. '
               'Defaults to store.'))

    # Define behaviour for --offset...
    argument_parser.add_argument(
        '--offset',
        default=1,
        dest='offset',
        nargs='?',
        type=int,
        help=_('Row offset to begin processing on with 1 being first after '
               'column header line.'))

    # Define behaviour for --threads...
    argument_parser.add_argument(
        '--threads',
        default=0,
        dest='threads',
        nargs='?',
        type=int,
        help=_('Number of concurrent import threads. Defaults to number of '
               'logical cores on server.'))

    # Define behaviour for --threads-max...
    argument_parser.add_argument(
        '--threads-max',
        default=8,
        dest='threads_maximum',
        nargs='?',
        type=int,
        help=_('Spawn no more than at most this many concurrent import '
               'threads. Defaults to 8.'))

# Class to batch import a bunch of songs at once. Uses multiple synchronized
#  processes...
class BatchSongImporter:

    # Constructor...
    def __init__(self, arguments, songs_total):

        self._arguments             = arguments
        self._errors_remaining      = arguments.maximum_errors
        self._executor              = None
        self._failures              = []
        self._queue                 = queue.Queue(self._arguments.threads) # maxsize=1
        self._songs_processed       = arguments.offset - 1
        self._songs_total           = songs_total
        self._stop_event            = threading.Event()
        self._thread_lock           = threading.Lock()

    # Consumer thread which submits music to server...
    def _add_song_consumer_thread(self, consumer_thread_index):

        logging.debug(_(F"consumer {consumer_thread_index}: Spawned."))

        # Create a client...
        client = helios.client(
            api_key=self._arguments.api_key,
            host=self._arguments.host,
            port=self._arguments.port,
            tls=self._arguments.tls,
            tls_ca_file=self._arguments.tls_ca_file,
            tls_certificate=self._arguments.tls_certificate,
            tls_key=self._arguments.tls_key,
            verbose=self._arguments.verbose)

        try:

            # Keep adding songs as long as we haven't been instructed to stop...
            while not self._stop_event.is_set():

                # Flag on whether adding the song was successful or not...
                success = False

                # On a failure for this song, log this message...
                failure_message = ""

                # Try to submit a song...
                try:

                    # Retrieve a csv_row, or block for at most one second before
                    #  checking to see if bail requested...
                    try:
                        logging.debug(_(F"consumer {consumer_thread_index}: Waiting for a job."))
                        csv_row = None
                        csv_row = self._queue.get(timeout=1)
                        reference = csv_row['reference']
                        logging.debug(_(F"consumer {consumer_thread_index}: {reference} Got a job."))
                        with self._thread_lock:
                            self._songs_processed += 1
                            logging.info(_(F"consumer {consumer_thread_index}: {reference} Processing song {self._songs_processed} of {self._songs_total}."))

                    # Queue is empty. Try again...
                    except queue.Empty:
                        logging.debug(_(F"consumer {consumer_thread_index}: Job queue empty, will try again."))
                        continue

                    # Check if the song already has been added, and if so, skip it...
                    try:
                        # Probe server to see if song already exists...
                        logging.debug(_(F"consumer {consumer_thread_index}: {reference} Checking if song already exists."))
                        client.get_song(song_reference=csv_row['reference'])
                        logging.info(_(F"consumer {consumer_thread_index}: {reference} Song already known to server, skipping."))

                        # It already exists. Treat this as a success and go to
                        #  next song...
                        success = True
                        continue

                    # Song doesn't aleady exist, so proceed to try to upload...
                    except helios.exceptions.NotFound:
                        pass

                    # Construct new song...
                    new_song_dict = {

                        'album' : csv_row.get('album'),
                        'artist' : csv_row.get('artist'),
                        'title' : csv_row.get('title'),
                        'genre' : csv_row.get('genre'),
                        'isrc' : csv_row.get('isrc'),
                        'beats_per_minute' : csv_row.get('beats_per_minute'),
                        'year' : csv_row.get('year'),
                        'file' : base64.b64encode(open(csv_row['path'], 'rb').read()).decode('ascii'),
                        'reference' : csv_row.get('reference')
                    }

                    # Upload if not a dry run...
                    if not self._arguments.dry_run:
                        client.add_song(
                            new_song_dict=new_song_dict,
                            store=self._arguments.store,
                            progress_callback=partial(
                                self._current_song_progress_callback, consumer_thread_index, reference))

                    # Otherwise log the pretend upload dry run...
                    else:
                        logging.info(_(F"consumer {consumer_thread_index}: {reference} Dry run uploading."))

                # JSON decoder error...
                except simplejson.errors.JSONDecodeError as some_exception:
                    failure_message = _(F"{str(some_exception)}")
                    logging.info(_(F"consumer {consumer_thread_index}: {reference} JSON decode error: {str(some_exception)}."))

                # Conflict...
                except helios.exceptions.Conflict as some_exception:
                    failure_message = _(F"{str(some_exception)}")
                    logging.info(_(F"consumer {consumer_thread_index}: {reference} Conflict error: {str(some_exception)}."))

                # Bad input...
                except helios.exceptions.Validation as some_exception:
                    failure_message = _(F"{str(some_exception)}")
                    logging.info(_(F"consumer {consumer_thread_index}: {reference} Validation failed: {str(some_exception)}."))

                # Connection failed...
                except helios.exceptions.Connection as some_exception:
                    failure_message = _(F"{str(some_exception)}")
                    logging.info(_(F"consumer {consumer_thread_index}: {reference} Connection problem ({str(some_exception)})."))

                # Server complained about request...
                except helios.exceptions.BadRequest as some_exception:
                    failure_message = _(F"Server said: {str(some_exception)}")
                    logging.info(_(F"consumer {consumer_thread_index}: {reference} Server said: {str(some_exception)}"))

                # Some other exception occured...
                except Exception as some_exception:

                    # Notify user...
                    failure_message = _(F"{str(some_exception)} ({type(some_exception)})")
                    logging.info(_(F"consumer {consumer_thread_index}: {reference} {str(some_exception)} ({type(some_exception)})."))

                    # Dump stack trace...
                    (exception_type, exception_value, exception_traceback) = sys.exc_info()
                    traceback.print_tb(exception_traceback)

                # Song added successfully without any issues...
                else:
                    success = True

                # In any event, update the total songs progress bar...
                finally:

                    # Notify thread formerly enqueued task is complete...
                    if csv_row is not None:
                        logging.debug(_(F"consumer {consumer_thread_index}: {reference} Moving to next song."))
                        self._queue.task_done()

                    # If we were not successful processing an actual song,
                    #  handle accordingly. But not when the work work queue is
                    #  simply empty which is not a meaningful failure...
                    if not success and csv_row is not None:

                        # Remember that this song created a problem...
                        self._failures.append((reference, failure_message))

                        # Decrement remaining permissible errors...
                        self._errors_remaining -= 1

                        # If no more permissible errors remaining, abort...
                        if (self._errors_remaining == -1) and (self._arguments.maximum_errors != 0):

                            # Alert user...
                            logging.info(_(F'consumer {consumer_thread_index}: Maximum errors reached (set to {self._arguments.maximum_errors}). Aborting...'))

                            # Signal to all threads to stop...
                            self._stop_event.set()

        # Some exception occurred that we weren't able to handle during the
        #  upload loop...
        except Exception as some_exception:
            logging.info(_(F'consumer {consumer_thread_index}: An exception occurred ({str(some_exception)}).'))

        # Log when we are exiting a consumer thread...
        logging.debug(_(F'consumer {consumer_thread_index}: Thread exited.'))

    # Progress bar callback...
    def _current_song_progress_callback(
        self, consumer_thread_index, reference, bytes_read, new_bytes, bytes_total):

        # If we're done uploading, update description to analysis stage...
        if bytes_read == bytes_total:
            logging.info(_(F'consumer {consumer_thread_index}: {reference} Upload complete. Awaiting server analysis...'))

       # time.sleep(0.001)

    # Get the number of errors remaining permitted...
    def get_errors_remaining(self):
        return self._errors_remaining

    # Get list of pairs of song references and failure messages for failed
    #  imports...
    def get_failures(self):
        return self._failures

    # Start batch import. This generates work for consumer threads...
    def start(self, csv_reader):

        logging.info(_(F"producer: Creating thread pool of {self._arguments.threads} threads."))

        # Construct consumer thread pool and run it...
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self._arguments.threads) as self._executor:

            try:
                # Spawn consumer threads and hand them a consumer thread index...
                for consumer_thread_index in range(0, self._arguments.threads):
                    self._executor.submit(
                        self._add_song_consumer_thread,
                        consumer_thread_index)

                # Create a job, while there is still work to be done...
                current_song_offset = 1
                for current_song_offset, data_frame in enumerate(csv_reader, 1):

                    # User requested to seek to given song offset, so do so.
                    #  Note that this is one more than absolute line offset
                    #  because first line are column headers...
                    if current_song_offset < self._arguments.offset:
                        continue

                    # Convert pandas data frame to single record as a vanilla
                    #  dictionary...
                    csv_row = data_frame.to_dict(orient='records')[0]

                    # Pandas has a number of issues we need to provide a
                    #  workaround for the csv_row before we can inject into the
                    #  consumer threads' work queue...
                    for key in csv_row:

                        # Because pandas struggles to distinguish a field
                        #  ommitted from an empty "" string field, we need to
                        #  clean up what it generated. Replace quoted strings
                        #  with their quoted contents...
                        if isinstance(csv_row[key], str) and len(csv_row[key]) >= 2:
                            if csv_row[key][0] == '"' and csv_row[key][-1] == '"':
                                csv_row[key] = csv_row[key][1:-1]

                        # Replace NaNs and NAs with None's so we can distinguish
                        #  from fields that were intentionally ommitted versus
                        #  ones that the user explicitly wanted a value of an
                        #  empty string...
                        if isinstance(csv_row[key], float) and numpy.isnan(csv_row[key]):
                            csv_row[key] = None

                        # Nullable integers weren't added until Panda 0.24.0.
                        #  Type cast the fields that were really suppose to be
                        #  integers from floats to integers...
                        if isinstance(csv_row[key], float) and (key in ("beats_per_minute", "year")):
                            csv_row[key] = int(csv_row[key])

                    logging.debug(_(F"producer: Loaded {csv_row['reference']} record."))

                    # Keep trying to add the job to the work queue until
                    #  successful or we are told to abort...
                    while not self._stop_event.is_set():

                        # Try to add job...
                        try:
                            logging.debug(_("producer: Waiting to add new work to work queue."))
                            self._queue.put(csv_row, timeout=1)
                            logging.debug(_(F"producer: Added {csv_row['reference']} record to work queue."))

                        # Queue is full, try again...
                        except queue.Full:
                            logging.debug(_("producer: Queue full, trying again."))
                            continue

                        # Done adding job. Go prepare next job...
                        break

                    if self._stop_event.is_set():
                        break

                # Drain work queue, while there is still work waiting to
                #  complete in consumer threads, and we have not been asked to
                #  abort...
                while not self._queue.empty() and not self._stop_event.is_set():
                    time.sleep(0.5)

                # Wait for all current work on the queue to be retrieved from
                #  consumer threads...
                logging.debug(_("producer: Completed submitting all work to work queue."))
                self.stop()
                logging.debug(_("producer: All work in work queue completed."))

            # Parser error, treated as fatal...
            except ValueError as some_exception:
                logging.error(_(F"producer: Song {current_song_offset}, parser error: {some_exception}."))

            # User trying to abort...
            except KeyboardInterrupt:
                print(_(F'\rAborting. Draining work queue of {self._queue.qsize()} items. Please wait a moment...'))
                self.stop()

            except Exception as some_exception:
                logging.error(_(F"producer: Exception: {str(some_exception)}."))

            except:
                logging.error(_("producer: Unhandled exception."))

            finally:
                logging.debug(_("producer: Done reading rows."))
                self.stop()

    # Gracefully stop all importation processes. Called from producer thread...
    def stop(self):

        # If stop has already been requested, don't try to join twice...
        if self._stop_event.is_set():
            #logging.debug('Stop already called.')
            return

        # Signal to all consumer threads to stop...
        logging.debug(_('Signally to all pending transactions to complete.'))
        self._stop_event.set()

        # Wait for all consumer threads to stop and work queue to drain...
        if self._executor:
            logging.debug(_(F'Waiting on work queue to drain {self._queue.qsize()} items.'))
            self._executor.shutdown(wait=True)
            logging.debug(_('Executor shutdown successfully.'))

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
    logging_format = "%(asctime)s: %(message)s"
    if arguments.verbose:
        logging.basicConfig(format=logging_format, level=logging.DEBUG, datefmt="%H:%M:%S")
    else:
        logging.basicConfig(format=logging_format, level=logging.INFO, datefmt="%H:%M:%S")

    # Success flag to determine exit code...
    success = False

    # Total number of songs in the input catalogue file...
    songs_total = 0

    # Batch importer will be constructed within try block...
    batch_importer = None

    # Try to process the catalogue file...
    try:

        # Input file...
        catalogue_file = None

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

        # Verify we can reach the server...
        server_status = client.get_server_status()

        # User requested autodetection on the number of consumer threads...
        if arguments.threads == 0:

            # Start by setting to the number of logical cores on the server...
            arguments.threads = max(server_status.cpu.cores, 1)

            # If the number of threads exceeds the maximum allowed, reduce it.
            #  This is a safety blow out valve in case the server has 144
            #  logical cores and the client spawns enough threads that they
            #  become i/o bound...
            if arguments.threads > arguments.threads_maximum:
                arguments.threads = arguments.threads_maximum

        # These column headers are expected...
        acceptable_field_names = [
            'reference',
            'album',
            'artist',
            'title',
            'genre',
            'isrc',
            'beats_per_minute',
            'year',
            'path'
        ]

        # These are the types for every acceptable header. Note that for
        #  beats_per_minute and year, these should be integral types, but
        #  nullable integers weren't added until Pandas 0.24.0...
        acceptable_field_types = {
            'reference'         : 'str',
            'album'             : 'str',
            'artist'            : 'str',
            'title'             : 'str',
            'genre'             : 'str',
            'isrc'              : 'str',
            'beats_per_minute'  : 'float',
            'year'              : 'float',
            'path'              : 'str'
        }

        # These headers are always required...
        required_field_names = [
            'reference',
            'path'
        ]

        # Open reader so we can verify headers and count records...
        reader = pandas.read_csv(
            filepath_or_buffer=arguments.catalogue_file,
            comment='#',
            compression='infer',
            delimiter=',',
            header=0,
            skip_blank_lines=True,
            iterator=True,
            chunksize=1,
            quotechar='"',
            quoting=0, # csv.QUOTE_MINIMAL
            doublequote=False,
            escapechar='\\',
            encoding='utf-8',
            low_memory=True)

        # Count the number of song lines in the input catalogue. We use the
        #  pandas reader to do this because it will only count actual song lines
        #  after the header and will skip empty lines...
        logging.info(_("Please wait while counting songs in input catalogue..."))
        for current_song_offset, data_frame in enumerate(reader, 1):

            # For the first record only, check headers since we only need to do
            #  this once...
            if current_song_offset == 1:

                # Check for any extraneous column fields and raise error if any...
                detected_field_names = data_frame.columns.tolist()
                extraneous_fields = list(set(detected_field_names) - set(acceptable_field_names))
                if len(extraneous_fields) > 0:
                    raise helios.exceptions.Validation(_(F"Input catalogue contained unrecognized column: {extraneous_fields}"))

                # Check for minimum required column fields and raise error if missing any...
                missing_fields = set(required_field_names) - set(detected_field_names)
                if len(missing_fields) > 0:
                    raise helios.exceptions.Validation(_(F"Input catalogue missing column field: {missing_fields}"))

            # Count one more song line...
            songs_total += 1

            # Every thousand songs give some feedback...
            if songs_total % 10 == 0:
                print(_(F"\rFound {songs_total:,} songs..."), end='', flush=True)

        # Provide summary and reset seek pointer for parser to next line after
        #  headers...
        print("\r", end='')
        logging.info(_(F"Counted a total of {songs_total:,} songs..."))

        # Now initialize the reader we will actually use to parse the records
        #  and supply the consumer threads...
        reader = pandas.read_csv(
            filepath_or_buffer=arguments.catalogue_file,
            comment='#',
            compression='infer',
            delimiter=',',
            dtype=acceptable_field_types,
            header=0,
            skipinitialspace=True,
            skip_blank_lines=True,
            iterator=True,
            na_values=[],
            chunksize=1,
            quotechar='"',
            quoting=0, # csv.QUOTE_MINIMAL
            doublequote=False,
            escapechar='\\',
            encoding='utf-8',
            low_memory=True)

        # Initialize batch song importer...
        batch_importer = BatchSongImporter(arguments, songs_total)

        # Submit the songs...
        batch_importer.start(reader)

        # Determine how we will exit...
        success = (arguments.maximum_errors == 0 or (batch_importer.get_errors_remaining() == arguments.maximum_errors))

    # User trying to abort...
    except KeyboardInterrupt:
        print(_('\rAborting, please wait a moment...'))
        success = False

    # Helios exception...
    except helios.exceptions.ExceptionBase as some_exception:
        print(some_exception.what())

    # Some other kind of exception...
    except Exception as some_exception:
        print(_(F"An exception occurred: {str(some_exception)}"))

    # Cleanup...
    finally:

        # Cleanup batch importer...
        if batch_importer:

            # Tell it to stop, if it hasn't already...
            batch_importer.stop()

            # If there were any failures, deal with them...
            if len(batch_importer.get_failures()) > 0:

                # Notify user...
                print(_(F"Import failed for {len(batch_importer.get_failures())} songs: "))

                # Try to open a log file...
                try:
                    log_file = open("helios_import_errors.log", "w")

                # Failed. Let user know...
                except OSError:
                    print(_("Could not save failed import list to current working directory."))

                # Show the reference for each failed song...
                for reference, failure_message in batch_importer.get_failures():

                    # Save to log file if opened...
                    if log_file:
                        log_file.write(_(F"{reference}\t{failure_message}\n"))

                    # Show on stderr as well...
                    print(_(F"  {reference}: {failure_message}"))

                # Close log file if open...
                if log_file:
                    log_file.close()

            # Mark it as deallocated...
            del batch_importer

            # If this was a dry run, remind the user...
            if arguments.dry_run:
                print(_("Note that this was a dry run."))

        # Close input catalogue file...
        if catalogue_file:
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
