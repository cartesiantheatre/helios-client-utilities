#!/usr/bin/python3
#
#   Helios, intelligent music.
#   Copyright (C) 2015-2024 Cartesian Theatre. All rights reserved.
#

# System imports...
import argparse
import datetime
from pprint import pprint
import sys

# Other imports...
import attr
import helios
from helios_client_utilities.common import add_common_arguments, TrainingSession, zeroconf_find_server
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

# Import learning example triplets from a Helios training session (.hts) stored
#  on disk and passed as a parameter to the 'import' action...
def import_learning_examples(client, arguments):

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

# Show summary of learning examples...
def show_learning_examples_summary(client, arguments):

    # Get the genres information...
    genres_information_list = client.get_genres_information()

    # Show each genre's information...
    for genre_information in genres_information_list:

        # If no genre available, annotate as such...
        if not genre_information.genre:
            genre_information.genre = _("(Unknown)")

        # Show genre and total number of songs belonging to it...
        print(F"{genre_information.genre:>16} : {genre_information.count:<10}")

    # Add some white space...
    print('')

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

            # Delete a learning example...
            case 'delete':
                success = delete_learning_example(client, arguments)

            # Import learning examples from disk...
            case 'import':
                success = import_learning_examples(client, arguments)

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

