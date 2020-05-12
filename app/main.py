import sys
import os
import logging
import config
import sec

try:
    logging.basicConfig(
        format=config.logging_format,
        datefmt=config.logging_date_format
    )
    logger = logging.getLogger(config.app_name)
    logger.setLevel(level=config.logging_level)
except Exception as error:
    raise error


def create_output_directories():
    if not os.path.exists(config.output_folder):
        logger.debug(f'Creating folder {config.output_folder}.')
        os.makedirs(config.output_folder)

    if not os.path.exists(config.output_cleaned_files):
        logger.debug(f'Creating folder {config.output_cleaned_files}.  Cleaned files will be placed here.')
        os.makedirs(config.output_cleaned_files)

    if not os.path.exists(config.output_log_files):
        logger.debug(f'Creating folder {config.output_log_files}.  Log files will be placed here.')
        os.makedirs(config.output_log_files)

    if not os.path.exists(config.output_data_files):
        logger.debug(f'Creating folder {config.output_data_files}.  Data files will be placed here.')
        os.makedirs(config.output_data_files)


def main():
    """
    This is the main part of the program.
    1) Create output directory if it does not exist
    2) Download the master zip files from sec
    3) Process and clean the master index files
    """
    create_output_directories()

    sec.download_master_zip()
    sec.process_master_index()


if __name__ == "__main__":
    try:
        logger.info(f"{config.app_name} - Begin")
        main()
        logger.info(f"{config.app_name} - End")

    except Exception as error:
        logger.exception(f'Encountered an exception: {error}')
        sys.exit(1)
