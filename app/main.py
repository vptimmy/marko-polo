import sys
import os
import logging
from config import Environment
import sec

try:
    ev = Environment()
    logging.basicConfig(
        format=ev.logging_format,
        datefmt=ev.logging_date_format,
    )
    log_writer = logging.FileHandler(os.path.join(ev.output_log_files, 'output.log'), mode='w')
    log_writer.setLevel('DEBUG')
    log_writer.setFormatter(logging.Formatter(fmt='%(asctime)s %(levelname)5s %(message)s'))

    logger = logging.getLogger(ev.app_name)
    logger.addHandler(log_writer)
    logger.setLevel(level=ev.logging_level)
except Exception as error:
    raise error


def create_output_directories():
    if not os.path.exists(ev.output_folder):
        logger.debug(f'Creating folder {ev.output_folder}.')
        os.makedirs(ev.output_folder)

    if not os.path.exists(ev.output_cleaned_files):
        logger.debug(f'Creating folder {ev.output_cleaned_files}.  Cleaned files will be placed here.')
        os.makedirs(ev.output_cleaned_files)

    if not os.path.exists(ev.output_log_files):
        logger.debug(f'Creating folder {ev.output_log_files}.  Log files will be placed here.')
        os.makedirs(ev.output_log_files)

    if not os.path.exists(ev.output_data_files):
        logger.debug(f'Creating folder {ev.output_data_files}.  Data files will be placed here.')
        os.makedirs(ev.output_data_files)


def main():
    """
    This is the main part of the program.
    1) Create output directories if they do not exist
    2) Download the master zip files from sec
    3) Process and clean the master index files
    """

    create_output_directories()
    sec.download_master_zip()
    sec.process_master_index()


if __name__ == "__main__":
    try:
        logger.info(f"{ev.app_name} - Begin")
        main()
        logger.info(f"{ev.app_name} - End")

    except Exception as error:
        logger.exception(f'Encountered an exception: {error}')
        sys.exit(1)
