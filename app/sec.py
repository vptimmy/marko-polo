import os
import logging
import zipfile
import multiprocessing
import urllib.request
import urllib.parse
from urllib.error import HTTPError

from config import Environment
from laundry import FilingCleaner
from finance import get_financial, generate_cik_to_ticker_dict
from process_and_prepare import ProcessAndPrepare
import db

import requests
from bs4 import BeautifulSoup
from datetime import datetime

ev = Environment()
logger = logging.getLogger(ev.app_name)


def remove_master_index_file():
    """ Remove the old master index file.  Since we append to the file we need to start with a fresh slate """
    try:
        os.remove(f'{ev.output_folder}/master.idx')
        logger.info(f'Deleted {ev.output_folder}/master.idx file.')
    except FileNotFoundError:
        pass


def remove_filing_files():
    """ Remove previously downloaded files """
    logger.info(f'Started deleting all cleaned files from {ev.output_cleaned_files}.')
    file_list = os.listdir(ev.output_cleaned_files)
    for file in file_list:
        if file.endswith(".txt"):
            os.remove(f'{ev.output_cleaned_files}/{file}')
    logger.info(f'Finished deleting all cleaned files from {ev.output_cleaned_files}.')


def parse_finance():
    tasks = ProcessAndPrepare()


def pad_string(string: str, padding_length=10, padding_character='0'):
    return string.rjust(padding_length, padding_character)


def append_master_index(zip_file):
    """
    Here we extract the the master.idx from the the zip file and append it to the our master.idx
    """
    with zipfile.ZipFile(zip_file) as edgar_file:
        logger.info(f'Started extracting {zip_file}.')
        zip_data = edgar_file.read('master.idx').splitlines()
        with open(f'{ev.output_folder}/master.idx', "a") as master_index:
            for line in zip_data:
                line = line.decode()

                # If this is a 10-Q filing then add it to the master index file
                if '|' in line and ev.sec_form_type in line and not line.startswith('CIK'):
                    master_index.write(f'{line}\n')
        logger.info(f'Finished extracting {zip_file}.')


def download_master_zip():
    """
    Retrieve quarter master.zip file from sec website for each given year and or quarter

    This is controlled by setting two variables in either your .env file
    or modifying config.py file.  The two variables are:

    sec_analyze_since_fy = 2020
    sec_analyze_quarter = QTR2

    Fiscal year says what years to get.  If sec_analyze_quarter is gone then it will default to QTR1, QTR2, QTR3, QTR4
    If you specify a quarter then it will process that quarter for the give fiscal year.

    The program defaults to 2020 and all quarters
    """

    remove_master_index_file()

    logger.info(f'Started retrieving edgar master zip files since {ev.sec_analyze_since_fy}.')
    year = int(ev.sec_analyze_since_fy)
    while year <= datetime.today().year:

        if ev.sec_analyze_quarter:
            quarters = [ev.sec_analyze_quarter]
        else:
            quarters = ['QTR1', 'QTR2', 'QTR3', 'QTR4']

        for quarter in quarters:
            try:
                # Download and save it
                zip_file = f'{ev.sec_website}/Archives/edgar/full-index/{year}/{quarter}/master.zip'
                save_to = f'{ev.output_folder}/{year}{quarter}.zip'

                logger.info(f'Started processing and retrieving {year} {quarter} master.zip.')

                urllib.request.urlretrieve(zip_file, save_to)
                append_master_index(save_to)
                os.remove(save_to)

                logger.info(f'Finished processing and retrieving master.zip.')

            except HTTPError as http_error:
                # The file does not exist.  No worries.  Probably a quarter in the future.
                logger.error(f'An error occurred while trying to retrieve the {year}{quarter} master.zip file. '
                             f'Error: {http_error}')
        year += 1
    logger.info(f'Finished retrieving edgar master zip files.')


class SEC:
    def __init__(self):
        self.cik_to_ticker_dict = generate_cik_to_ticker_dict()

    def download_and_clean_filing(self, data_dict: dict):
        """
        We are passed a dictionary that contains the url of the overview of the 10-Q report and the CIK of the company.
        1) Download the overview 10-Q report
        2) Parse the report and find the 'Accepted Date'
        3) Gather any financial data from Yahoo about the 10-Q report
        4) If financial data was found the download the 10-Q report and strip out most the HTML.  Used later
           to compare to a previous quarter 10-Q report.  Used for the AI part.
        """
        url = data_dict['url']
        cik = pad_string(data_dict['cik'])

        logger.info(f'CIK: {cik} Processing {url}')
        try:
            response = requests.get(url)
        except requests.exceptions.ConnectionError as connection_error:
            logger.error(f'CIK: {cik} Encountered an error connecting to {url}.  Error: {connection_error}')
            return {}

        soup = BeautifulSoup(response.content.decode('utf-8'), "lxml")
        documents = soup.find('table', {'class': 'tableFile', 'summary': 'Document Format Files'})
        if documents:
            for tr in documents.find_all('tr'):
                td = tr.find_all('td')
                if len(td) >= 4 and td[3].text == ev.sec_form_type:
                    filing_url = td[2].find('a', href=True)
                    filing_href = filing_url['href']
                    data_dict['date_accepted'] = soup.find('div', attrs={'class': 'infoHead'}, text='Accepted')\
                                                     .findNext('div', {'class': 'info'}).text

                    logger.debug(f'CIK: {cik} Started checking for financial data.')
                    finance_data = get_financial(data_dict, self.cik_to_ticker_dict)
                    logger.debug(f'CIK: {cik} Finished checking for financial data.')
                    if finance_data:
                        if 'ix?' in filing_href:
                            filing_href = '/' + '/'.join(filing_href.split('/')[2:])

                        response = requests.request('GET', ev.sec_website + filing_href)
                        logger.debug(f'CIK: {cik} Started cleaning file.')
                        laundry = FilingCleaner(response.text, data_dict)
                        finance_data['file_name'] = laundry.wash()
                        logger.debug(f'CIK: {cik} Finished cleaning file.')

                        # Insert this record into the database
                        db.insert_into_finance(finance_data)

    def process_master_index(self):
        """
        Process the master.idx located in the output directory.  This was done previously (below).

        Process each line of the master.idx file.  This file in delimited by pipe symbol '|'
        For each line we extract the data then we download and clean the 10-Q.
        """
        cik_to_ticker_dict = generate_cik_to_ticker_dict()

        # Remove all the old cleaned filings and truncate the database
        remove_filing_files()
        db.truncate_finance()

        # Created by download_master_zip function below.
        master_index = open(f'{ev.output_folder}/master.idx')
        lines = master_index.read().splitlines()
        master_index.close()

        filings_to_download_and_clean = list()
        for line in lines:
            (cik, company_name, form_type, date_filed, file_name) = line.split('|')
            if form_type == ev.sec_form_type:
                filings_to_download_and_clean.append({
                    'url': f'{ev.sec_website}/Archives/{file_name.replace(".txt", "-index.html")}',
                    'cik': cik,
                    'date_filed': date_filed,
                    'company_name': company_name
                })

        with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
            logger.info(f'Started processing files. Number of CPU\'s: {multiprocessing.cpu_count()}')
            pool.map(self.download_and_clean_filing, filings_to_download_and_clean)
            logger.info('Finished processing files.')
        pool.close()
        pool.join()

        # Now parse and prepare the finance.json file
        parse_finance()
