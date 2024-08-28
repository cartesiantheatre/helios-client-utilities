#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2024 Cartesian Theatre. All rights reserved.
#

# System imports...
import argparse
import csv # For csv.QUOTE_NONNUMERIC constant...
from datetime import datetime
from pprint import pprint
import sys

# Other imports...
import attr
import helios
from helios_client_utilities.common import add_common_arguments, TrainingSession, zeroconf_find_server
import pandas
from termcolor import colored
from tqdm import tqdm

# i18n...
import gettext
_ = gettext.gettext

# Add arguments specific to this utility to argument parser...
def add_arguments(argument_parser):

    # Create a subparser for all the different types of action verbs...
    subparsers = argument_parser.add_subparsers(
        dest='action',
        required=True)

    # Create parser for 'add' action...
    add_parser = subparsers.add_parser('add')

    # Define behaviour for add --anchor...
    add_parser.add_argument(
        '--anchor',
        dest='anchor_song_reference',
        required=True,
        nargs='?',
        help=_('Anchor song reference.'))

    # Define behaviour for add --positive...
    add_parser.add_argument(
        '--positive',
        dest='positive_song_reference',
        required=True,
        nargs='?',
        help=_('Positive song reference.'))

    # Define behaviour for add --negative...
    add_parser.add_argument(
        '--negative',
        dest='negative_song_reference',
        required=True,
        nargs='?',
        help=_('Negative song reference.'))

    # Create subparser for 'create-csv' action...
    examine_parser = subparsers.add_parser('create-csv')

    # Define behavior for create-csv training session argument...
    examine_parser.add_argument(
        dest='hts_file',
        action='store',
        type=str,
        help=_('.hts file to read list of examined songs from'))

    # Define behavior for create-csv master CSV catalogue argument...
    examine_parser.add_argument(
        dest='csv_file',
        action='store',
        type=str,
        help=_('.csv file to find songs referenced in training session'))

    # Create parser for 'delete' action...
    delete_parser = subparsers.add_parser('delete')

    # Define behaviour for add --anchor...
    delete_parser.add_argument(
        '--anchor',
        dest='anchor_song_reference',
        required=True,
        nargs='?',
        help=_('Anchor song reference.'))

    # Define behaviour for add --positive...
    delete_parser.add_argument(
        '--positive',
        dest='positive_song_reference',
        required=True,
        nargs='?',
        help=_('Positive song reference.'))

    # Define behaviour for add --negative...
    delete_parser.add_argument(
        '--negative',
        dest='negative_song_reference',
        required=True,
        nargs='?',
        help=_('Negative song reference.'))

    # Create subparser for 'examine' action...
    examine_parser = subparsers.add_parser('examine')

    # Define behavior for examine file action...
    examine_parser.add_argument(
        dest='hts_file',
        action='store',
        type=str,
        help=_('.hts file to examine'))

    # Create subparser for 'import' action...
    import_parser = subparsers.add_parser('import')

    # Define behavior for import action file...
    import_parser.add_argument(
        dest='hts_file',
        action='store',
        type=str,
        help=_('.hts file to import'))

    # Create subparser for 'list' action...
    list_parser = subparsers.add_parser('list')

    # Create parser for 'purge' action...
    purge_parser = subparsers.add_parser('purge')

    # Create parser for 'summary' action...
    summary_parser = subparsers.add_parser('summary')

    # Create parser for 'train' action...
    train_parser = subparsers.add_parser('train')

# Add a learning example...
def add_learning_example(client, arguments):

    # Add the learning example...
    client.add_learning_example(
        arguments.anchor_song_reference,
        arguments.positive_song_reference,
        arguments.negative_song_reference)

    # Notify user of success...
    print(_("Learning example submitted successfully."))

    # Report success...
    return True

# Examine a .hts file on disk, cross referencing examined songs in,
#  a CSV file, and generating a new CSV to stdout only containing
#  the examined songs...
def create_csv(arguments):

    # Construct a training session...
    training_session = TrainingSession()

    # Load from disk...
    training_session.load(arguments.hts_file)

    # Get the set references for every song the user listened to...
    all_songs_listened_to = training_session.get_all_song_references()

    # These are the types for every acceptable header. Note that for
    #  beats_per_minute and year, these should be integral types, but nullable
    #  integers weren't added until Pandas 0.24.0...
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

    # Open CSV catalogue reader...
    reader = pandas.read_csv(
        filepath_or_buffer=arguments.csv_file,
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

    # Whether we've printed headers to stdout already or not. Will be untoggled
    #  after printing the first time...
    header=True

    # Shell exit status flag...
    success=True

    # Examine every record in the CSV file...
    for data_frame in reader:

        # Get the Panda series or row for the current song...
        series = data_frame.get('reference')

        # Get the song row's reference...
        reference = series.values[0]

        # If this song is one the user listened to...
        if reference in all_songs_listened_to:

            # Format the CSV line...
            line = data_frame.to_csv(
                None,
                index=False,
                header=header,
                quotechar='"',
                quoting=csv.QUOTE_NONNUMERIC,
                escapechar='\\',
                encoding='utf-8')

            # Print it to stdout...
            print(line, end='')

            # Don't show headers again...
            header = False

            # Make note that this song the user listened to was found in the CSV
            #  catalogue...
            all_songs_listened_to.remove(reference)

    # Were any songs remaining that the user listened to that weren't found in
    #  the provided CSV catalogue?
    for remaining_reference in all_songs_listened_to:

        # Log warning...
        print(F'Warning: Not found {remaining_reference}', file=sys.stderr)

    # If there were any songs not found, the shell should note an error...
    if len(all_songs_listened_to) > 0:
        success = False

    # Report success status...
    return success

# Delete all learning examples...
def delete_all_learning_examples(client, argument):

    # Get system status...
    system_status = client.get_system_status()

    # Prompt user to make sure they are certain they know what they are doing...
    verification = input(_(F"Are you sure you want to purge {system_status.learning.examples} learning examples? Type \'YES\': "))
    if verification != _('YES'):
        return False

    # Perform purge...
    client.delete_all_learning_examples()

    # Show how many we deleted...
    print(_(F"All learning examples purged successfully."))

    # Report success...
    return True

# Delete a learning example...
def delete_learning_example(client, arguments):

    # Delete the learning example...
    client.delete_learning_example(
        arguments.anchor_song_reference,
        arguments.positive_song_reference,
        arguments.negative_song_reference)

    # Notify user of success...
    print(_("Learning example deleted successfully."))

    # Report success...
    return True

# Examine a Helios training session (.hts) stored on disk and passed as a
#  parameter to the 'examine' action...
def examine_training_session(arguments):

    # Construct a training session...
    training_session = TrainingSession()

    # Load from disk...
    training_session.load(arguments.hts_file)

    # Show information about training session...
    print(_(F"Session:"))
    print(_(F"  Total songs listened to: {training_session.get_total_songs_listened()}"))
    print(_(F"  Total learning examples: {training_session.get_total_examples()}"))
    print(_(F"Expert:"))
    print(_(F"  Name: {training_session.get_expert_name()}"))
    print(_(F"  Email: {training_session.get_expert_email()}"))
    print(_(F"Date: {training_session.get_datetime()}"))
    print(_(F"Server:"))
    print(_(F"  Host: {training_session.get_host()}"))
    print(_(F"  Port: {training_session.get_port()}"))
    print(_(F"  TLS: {training_session.get_tls()}"))
    print(_(F"  Version: {training_session.get_version()}"))
    print(_(F"  API Key: {training_session.get_api_key()}"))
    print(_(F"Date: {training_session.get_datetime()}"))

    # Report success...
    return True

# Import learning example triplets from a Helios training session (.hts) stored
#  on disk and passed as a parameter to the 'import' action...
def import_training_session(client, arguments):

    # Construct a training session...
    training_session = TrainingSession()

    # Load from disk...
    training_session.load(arguments.hts_file)

    # Get examples from user's training session...
    learning_example_triplets = training_session.get_examples()

    # Notify user...
    print(_(F"Uploading {len(learning_example_triplets)} learning examples. Please wait..."))

    # Upload to server...
    client.add_learning_examples(learning_example_triplets)

    # Report success...
    return True

# List all learning examples...
def list_learning_examples(client, arguments):

    # Get all learning examples...
    learning_examples = client.get_learning_examples()

    # Show each one...
    for learning_example in learning_examples:
        print(_(F"Anchor: {learning_example.anchor}"))
        print(_(F"Positive: {learning_example.positive}"))
        print(_(F"Negative: {learning_example.negative}"))
        print()

    # Report success...
    return True

# Perform training on learning examples...
def perform_training(client, arguments):

    # Perform training...
    training_report = client.perform_training(tui_progress=True)

    # Show report...
    print(_("Training complete..."))
    print(_(F"\tGPU Accelerated: {training_report.gpu_accelerated}"))
    print(_(F"\tTotal Time: {str(datetime.timedelta(seconds=training_report.total_time))}"))

    # Report success...
    return True

# Show summary of learning examples on server...
def show_learning_examples_summary(client, arguments):

    # Get system status...
    system_status = client.get_system_status()

    # Show general information...
    print(_(F"Learning examples: {system_status.learning.examples:<10}"))
    print(_(F"Last trained     : {system_status.learning.last_trained}"))
    print(_(F"Total songs      : {system_status.songs:<10}"))

    # Report success...
    return True

# Main function...
def main():

    # Initialize the argument parser...
    argument_parser = argparse.ArgumentParser(
        description=_('Perform machine learning related tasks on a Helios server.'))

    # Add common arguments to argument parser...
    add_common_arguments(argument_parser)

    # Add arguments specific to this utility to argument parser...
    add_arguments(argument_parser)

    # Parse the command line...
    arguments = argument_parser.parse_args()

    # Success flag to determine exit code...
    success = False

    # Try to perform the requested action...
    try:

        # Check command line was sane...
        if arguments.action in ['add', 'delete'] and (None in [arguments.anchor_song_reference, arguments.positive_song_reference, arguments.negative_song_reference]):
            raise Exception(_(F"The \"{arguments.action}\" action requires an anchor, positive, and negative song references."))

        # Client to be constructed, if necessary...
        client = None

        # For every action, other than these, probe the LAN if necessary for a
        #  server and construct a client...
        if arguments.action not in ['create-csv', 'examine']:

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

        # Perform the requested action...
        match arguments.action:

            # Add a learning example...
            case 'add':
                success = add_learning_example(client, arguments)

            # Examine a .hts file on disk, cross referencing examined songs in,
            #  a CSV file, and generating a new CSV to stdout only containing
            #  the examined songs...
            case 'create-csv':
                success = create_csv(arguments)

            # Delete a learning example...
            case 'delete':
                success = delete_learning_example(client, arguments)

            # Examine a .hts file on disk...
            case 'examine':
                success = examine_training_session(arguments)

            # Import learning examples from a .hts file on disk...
            case 'import':
                success = import_training_session(client, arguments)

            # List all learning examples...
            case 'list':
                success = list_learning_examples(client, arguments)

            # Delete all learning examples...
            case 'purge':
                success = delete_all_learning_examples(client, arguments)

            # Show a summary of learning examples...
            case 'summary':
                success = show_learning_examples_summary(client, arguments)

            # Train the system based on currently available learning examples...
            case 'train':
                success = perform_training(client, arguments)

        # Note the success...
        success = True

    # User trying to abort...
    except KeyboardInterrupt:
        sys.exit(1)

    # Helios exception...
    except helios.exceptions.ExceptionBase as some_exception:
        print(some_exception.what())

    # Some other kind of exception...
    except Exception as some_exception:
        print(_(f"An exception occurred: {str(some_exception)}"))

    # Cleanup...
    finally:
        pass

    # If unsuccessful, bail...
    if not success:
        sys.exit(1)

    # Done...
    sys.exit(0)

# Entry point...
if __name__ == '__main__':
    main()

