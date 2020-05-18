import sys
import os
import logging
from config import Environment
from sec import SEC, download_master_zip
import db
import differences
from pathlib import Path
import pandas
from datetime import datetime

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

    log_writer = logging.FileHandler(os.path.join(ev.output_log_files, f'{datetime.now()}-output.log'), mode='w')
    log_writer.setFormatter(logging.Formatter(fmt='%(asctime)s %(levelname)5s %(message)s'))
    log_writer.setLevel('DEBUG')
    logger.addHandler(log_writer)
except Exception as error:
    raise error


def create_csv():
    conn = db.connect_to_db()
    sql = '''SELECT
                 difference_from_last_report as differ,
                 prc_change2 
             FROM 
                 marko_finance 
             WHERE 
                 prc_change2 IS NOT NULL AND
                 difference_from_last_report IS NOT NULL'''
    finance = pandas.read_sql_query(sql, conn)
    finance['prc_change2'] = pandas.qcut(finance.prc_change2.astype(float), q=5, labels=range(5))
    finance['differ'] = finance.differ.str.replace(r'\r|\n', ' ').replace(r'"', '')
    finance.to_csv('training_data.csv', header=False, index=False)
    conn.close()


def main():
    """
    This is the main part of the program.
    1) Create output directories if they do not exist
    2) Download the master zip files from sec
    3) Process and clean the master index files
    """

    # Create output folder and database
    db.create_finance_table()

    if ev.create_report:
        create_csv()
    elif ev.get_differences:
        differences.get_differences()
        create_csv()
    else:
        sec = SEC()
        download_master_zip()
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
