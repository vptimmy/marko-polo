import sys
import os
import logging
from config import Environment
from sec import SEC, download_master_zip
import db
import differences
from pathlib import Path

try:
    ev = Environment()
    Path(ev.output_log_files).mkdir(parents=True, exist_ok=True)
    Path(ev.output_db).mkdir(parents=True, exist_ok=True)
    Path(ev.output_cleaned_files).mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        format=ev.logging_format,
        datefmt=ev.logging_date_format,
    )
    logger = logging.getLogger(ev.app_name)
    logger.setLevel(level=ev.logging_level)

    log_writer = logging.FileHandler(os.path.join(ev.output_log_files, 'output.log'), mode='w')
    log_writer.setFormatter(logging.Formatter(fmt='%(asctime)s %(levelname)5s %(message)s'))
    log_writer.setLevel('DEBUG')
    logger.addHandler(log_writer)
except Exception as error:
    raise error


def create_csv():
    pass


def main():
    """
    This is the main part of the program.
    1) Create output directories if they do not exist
    2) Download the master zip files from sec
    3) Process and clean the master index files
    """

    # Create output folder and database
    db.create_finance_table()

    if ev.app_create_report:
        create_csv()

    elif ev.app_get_differences:
        differences.get_differences()
        create_csv()
    else:
        # If the master index does not exist then download a new one.
        if not os.path.exists(os.path.join(ev.output_folder, 'master.idx')):
            download_master_zip()

        sec = SEC()
        sec.process_master_index()
        differences.get_differences()
        create_csv()


if __name__ == "__main__":
    try:
        logger.info(f"{ev.app_name} - Begin")
        main()
        logger.info(f"{ev.app_name} - End")

    except Exception as error:
        logger.exception(f'Encountered an exception: {error}')
        sys.exit(1)
