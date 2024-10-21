#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2024 Cartesian Theatre. All rights reserved.
#

# System imports...
import argparse
import csv # For csv.QUOTE_NONNUMERIC constant...
from datetime import datetime
import json
import os
from pprint import pprint
import shutil
import sys
import tempfile

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
    add_example_parser = subparsers.add_parser('add-example')

    # Define behaviour for add --anchor...
    add_example_parser.add_argument(
        '--anchor',
        dest='anchor_song_reference',
        required=True,
        nargs='?',
        help=_('Anchor song reference.'))

    # Define behaviour for add --positive...
    add_example_parser.add_argument(
        '--positive',
        dest='positive_song_reference',
        required=True,
        nargs='?',
        help=_('Positive song reference.'))

    # Define behaviour for add --negative...
    add_example_parser.add_argument(
        '--negative',
        dest='negative_song_reference',
        required=True,
        nargs='?',
        help=_('Negative song reference.'))

    # Create subparser for 'create-catalogue' action...
    create_catalogue_parser = subparsers.add_parser('create-catalogue')

    # Define behavior for create-catalogue training session argument...
    create_catalogue_parser.add_argument(
        dest='training_session_file',
        action='store',
        type=str,
        help=_('An .hts training session to read list of user\'s songs they listened to.'))

    # Define behavior for create-catalogue master CSV catalogue argument...
    create_catalogue_parser.add_argument(
        dest='csv_master_file',
        action='store',
        type=str,
        help=_('Master .csv file that contains every song referenced in training session.'))

    # Define behavior for create-catalogue subset CSV catalogue argument...
    create_catalogue_parser.add_argument(
        dest='csv_output_file',
        action='store',
        type=str,
        help=_('Output .csv file that contains a subset of only those songs the user listened to in their training session.'))

    # Define behaviour for --ignore-orphaned-references...
    create_catalogue_parser.add_argument(
        '--ignore-orphaned-references',
        action='store_true',
        default=False,
        dest='ignore_orphaned_references',
        help=_('Treat orphaned song references as warnings rather than errors.'))

    # Define behaviour for add --output-music-dir...
    create_catalogue_parser.add_argument(
        '--output-music-dir',
        dest='output_music_dir',
        required=False,
        nargs='?',
        help=_('Optionally copy all music the user listened to into this directory.'))

    # Define behaviour for add --copy-music...
    create_catalogue_parser.add_argument(
        '--output-prefix-dir',
        dest='output_prefix_dir',
        required=False,
        nargs='?',
        help=_('Optionally substitute the leading path in the \'path\' CSV field in the csv_output_file with this.'))

    # Create parser for 'delete-example' action...
    delete_example_parser = subparsers.add_parser('delete-example')

    # Define behaviour for add --anchor...
    delete_example_parser.add_argument(
        '--anchor',
        dest='anchor_song_reference',
        required=True,
        nargs='?',
        help=_('Anchor song reference.'))

    # Define behaviour for add --positive...
    delete_example_parser.add_argument(
        '--positive',
        dest='positive_song_reference',
        required=True,
        nargs='?',
        help=_('Positive song reference.'))

    # Define behaviour for add --negative...
    delete_example_parser.add_argument(
        '--negative',
        dest='negative_song_reference',
        required=True,
        nargs='?',
        help=_('Negative song reference.'))

    # Create parser for 'delete-model' action...
    delete_model_parser = subparsers.add_parser('delete-model')

    # Create subparser for 'examine-session' action...
    examine_session_parser = subparsers.add_parser('examine-session')

    # Define behavior for examine-session file action...
    examine_session_parser.add_argument(
        dest='training_session_file',
        action='store',
        type=str,
        help=_('.hts file to examine'))

    # Create subparser for 'import-examples' action...
    import_examples_parser = subparsers.add_parser('import-examples')

    # Define behavior for import-examples action file...
    import_examples_parser.add_argument(
        dest='training_session_file',
        action='store',
        type=str,
        help=_('.hts file to import'))

    # Create subparser for 'list-examples' action...
    list_examples_parser = subparsers.add_parser('list-examples')

    # Create subparser for 'load-model' action...
    load_model_parser = subparsers.add_parser('load-model')

    # Define behavior for import-examples action file...
    load_model_parser.add_argument(
        dest='model_file',
        action='store',
        type=str,
        help=_('.hml file to import'))

    # Create parser for 'purge-examples' action...
    purge_examples_parser = subparsers.add_parser('purge-examples')

    # Create subparser for 'save-model' action...
    save_model_parser = subparsers.add_parser('save-model')

    # Define behavior for save-model action file...
    save_model_parser.add_argument(
        dest='model_file',
        action='store',
        type=str,
        help=_('.hml file to save to'))

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

# Examine a .hts file on disk, cross referencing examined songs in, a CSV file,
#  and generating a new CSV to stdout only containing the examined songs...
def create_catalogue(arguments):

    # Construct a training session...
    training_session = TrainingSession()

    # Load from disk...
    training_session.load(arguments.training_session_file)

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

    # Make sure output CSV path is an absolute path...
    arguments.csv_output_file = os.path.abspath(arguments.csv_output_file)

    # Get just the CSV output directory...
    csv_output_directory = os.path.dirname(arguments.csv_output_file)

    # Create it if it doesn't exist already...
    os.makedirs(csv_output_directory, exist_ok=True)

    # CSV output file stream file descriptor, stream, and temporary name...
    csv_output_stream_fd        = None
    csv_output_stream           = None
    csv_output_tempfile_name    = None

    # Array of file copying related errors to append to as they arise. They will
    #  be printed to stderr after all batch processing is completed...
    copy_errors = []

    # Try to remove a previous output CSV file, if any...
    try:
        os.remove(arguments.csv_output_file)

    # If the file already does not exist, that's fine...
    except FileNotFoundError:
        pass

    # Create the CSV output file in a temporary location which will be moved in
    #  place to arguments.csv_output_file upon successful generation to avoid
    #  the user accidentally using a truncated output from an unsuccessful
    #  generation...
    [csv_output_stream_fd, csv_output_tempfile_name] = tempfile.mkstemp(
        prefix='helios_learn_output_csv', text=True)

    # Open the file descriptor as a normal stream...
    csv_output_stream = os.fdopen(csv_output_stream_fd, 'w')

    # Open CSV catalogue reader...
    reader = pandas.read_csv(
        filepath_or_buffer=arguments.csv_master_file,
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

    # Whether we've output the headers already or not. Will be untoggled after
    #  printing the first time...
    header=True

    # Shell exit status flag...
    success=True

    # Track how many songs are in the new catalogue...
    catalogue_size = 0

    # Did the user request to copy the songs listened to somewhere?
    if arguments.output_music_dir:

        # Make sure song output directory is an absolute path...
        arguments.output_music_dir = os.path.abspath(arguments.output_music_dir)

        # Create it if it doesn't exist already...
        os.makedirs(arguments.output_music_dir, exist_ok=True)

    # Examine every record in the master CSV file...
    for data_frame in reader:

        # Get the Panda series or row for the current song...
        series = data_frame.get('reference')

        # Get the song row's reference...
        reference = series.values[0]

        # If this song is not a song the user listened to, skip it...
        if reference not in all_songs_listened_to:
            continue

        # If the user specified a directory to copy songs into, then use it...
        if arguments.output_music_dir:

            # Get the song's path...
            series = data_frame.get('path')
            song_path = series.values[0]

            # Make sure it is absolute...
            song_path = os.path.abspath(song_path)

            # Try to copy the song into the requested output directory...
            try:

                # Perform copy...
                shutil.copy(song_path, arguments.output_music_dir)

                # Log it...
                print(_(F'{os.path.basename(song_path)}'))

            # Something bad happened. Remember for later...
            except Exception as some_exception:
                copy_errors.append(_(F'{reference}: {str(some_exception)}'))

        # If the user specified a path substitution prefix, then use it...
        if arguments.output_prefix_dir:

            # Get the song's path...
            series = data_frame.get('path')
            song_path = series.values[0]

            # Substitute the leading path, leaving the file name as is...
            song_path = os.path.join(arguments.output_prefix_dir, os.path.basename(song_path))

            # Get absolute path...
            song_path = os.path.abspath(song_path)

            # Replace the old song path with the new one in the data frame...
            series.values[0] = song_path

        # Format the CSV line...
        line = data_frame.to_csv(
            None,
            index=False,
            header=header,
            quotechar='"',
            quoting=csv.QUOTE_NONNUMERIC,
            escapechar='\\',
            encoding='utf-8')

        # Write line to output CSV file...
        csv_output_stream.write(line)

        # Don't show headers again...
        header = False

        # Make note that this song the user listened to was found in the CSV
        #  catalogue...
        all_songs_listened_to.remove(reference)

        # Update statistics...
        catalogue_size += 1

    # Close temporary output CSV file...
    os.close(csv_output_stream_fd)

    # Move the temporary output CSV file into location expected by user...
    shutil.move(csv_output_tempfile_name, arguments.csv_output_file)

    # If any errors occurred while attempting to copy music files...
    if len(copy_errors) > 0:

        # Show header...
        print(_(F'Warning: Errors occurred while coping the following songs referenced in {os.path.basename(arguments.csv_master_file)}:'), file=sys.stderr)

        # Dump each error...
        for error in copy_errors:
            print(_(F'  {error}'), file=sys.stderr)

        # Note to shell there were some errors...
        success = False

    # Were any songs remaining that the user listened to that weren't found in
    #  the provided CSV catalogue?
    if len(all_songs_listened_to) > 0:

        # Show header...
        print(_(F'Warning: Song references found in {os.path.basename(arguments.training_session_file)} not found in {os.path.basename(arguments.csv_master_file)}:'), file=sys.stderr)

        # Dump each warning...
        for remaining_reference in all_songs_listened_to:
            print(_(F'  {remaining_reference}'), file=sys.stderr)

        # Unless the user opted to ignore references that could not be found in
        #  the master CSV, inform shell there was a problem...
        if arguments.ignore_orphaned_references is False:
            success = False

    # Show statistics...
    print(_(F'Created new catalogue of {catalogue_size} songs...'))

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

# Delete the currently loaded learning model, reverting back to default...
def delete_learning_model(client, arguments):

    # Delete it...
    client.delete_learning_model()

    # Report success...
    return True

# Examine a Helios training session (.hts) stored on disk and passed as a
#  parameter to the 'examine' action...
def examine_training_session(arguments):

    # Construct a training session...
    training_session = TrainingSession()

    # Load from disk...
    training_session.load(arguments.training_session_file)

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

    # Report success...
    return True

# Import learning example triplets from a Helios training session (.hts) stored
#  on disk and passed as a parameter to the 'import' action...
def import_training_session(client, arguments):

    # Construct a training session...
    training_session = TrainingSession()

    # Load from disk...
    training_session.load(arguments.training_session_file)

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

# Load learning model...
def load_learning_model(client, arguments):

    # Upload and load the learning model...
    client.load_learning_model(arguments.model_file)

    # Notify user...
    print(_("Successfully loaded new learning model..."))

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

# Save learning model...
def save_learning_model(client, arguments):

    # Retrieve the learning model...
    learning_model = client.get_learning_model()

    # Construct learning model schema to transform learning model into JSON to
    #  save to disk...
    learning_example_schema = helios.requests.LearningModelSchema()

    # Convert to JSON...
    json_data = learning_example_schema.dumps(learning_model)

    # Convert to a dict and insert a dummy field to assist shell in identifying
    #  file type...
    json_dict = json.loads(json_data)
    json_dict["helios_learning_model"] = "file_magic"

    # Check to ensure output file name has expected file extension, and if not,
    #  add it...
    filename, extension = os.path.splitext(arguments.model_file)
    arguments.model_file = F'{filename}.hml'

    # Save it to disk...
    with open(arguments.model_file, "w") as file:
        json.dump(json_dict, file, sort_keys=True)

    # Notify user...
    print(_(F"Learning model saved successfully to {arguments.model_file}"))

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
        if arguments.action in ['add-example', 'delete-example'] and (None in [arguments.anchor_song_reference, arguments.positive_song_reference, arguments.negative_song_reference]):
            raise Exception(_(F"The \"{arguments.action}\" action requires an anchor, positive, and negative song references."))

        # Client to be constructed, if necessary...
        client = None

        # For every action, other than these, probe the LAN if necessary for a
        #  server and construct a client...
        if arguments.action not in ['create-catalogue', 'examine-session']:

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
            case 'add-example':
                success = add_learning_example(client, arguments)

            # Examine a .hts file on disk, cross referencing examined songs in,
            #  a CSV file, and generating a new CSV to stdout only containing
            #  the examined songs...
            case 'create-catalogue':
                success = create_catalogue(arguments)

            # Delete a learning example...
            case 'delete-example':
                success = delete_learning_example(client, arguments)

            # Delete a learning model...
            case 'delete-model':
                success = delete_learning_model(client, arguments)

            # Examine a .hts file on disk...
            case 'examine-session':
                success = examine_training_session(arguments)

            # Import learning examples from a .hts file on disk...
            case 'import-examples':
                success = import_training_session(client, arguments)

            # Load a learning model from a .hml file on disk...
            case 'load-model':
                success =  load_learning_model(client, arguments)

            # List all learning examples...
            case 'list-examples':
                success = list_learning_examples(client, arguments)

            # Delete all learning examples...
            case 'purge-examples':
                success = delete_all_learning_examples(client, arguments)

            # Save a learning model to a .hml file on disk...
            case 'save-model':
                success =  save_learning_model(client, arguments)

            # Show a summary of learning examples...
            case 'summary':
                success = show_learning_examples_summary(client, arguments)

            # Train the system based on currently available learning examples...
            case 'train':
                success = perform_training(client, arguments)

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

