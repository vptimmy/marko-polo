import os
import logging
import zipfile
import multiprocessing
import urllib.request
import urllib.parse
from urllib.error import HTTPError
import json

from config import Environment
from laundry import FilingCleaner

import requests
import yfinance as yf
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

ev = Environment()
logger = logging.getLogger(ev.app_name)

cik_to_ticker_dict = dict()


def build_dict_from_ticker():
    """
    Download the ticker.txt file from SEC.

    @todo Need to add the ability to add your own CIK:Ticker symbol via a file in the input directory.
    """
    global cik_to_ticker_dict
    logger.info(f'Getting ticker / cik map from {ev.sec_ticker_url}.')
    ticker = requests.get(ev.sec_ticker_url)
    lines = ticker.text.splitlines()
    for line in lines:
        (ticker_symbol, cik) = line.split('\t')
        cik_to_ticker_dict[cik] = ticker_symbol

    with open(os.path.join(ev.dir_path, 'input', 'cik_to_ticker.txt')) as cik_input:
        for line in cik_input:
            if not line.startswith('#') and len(line) > 5:
                cik, ticker = line.strip().split(' ')
                if cik and ticker:
                    cik_to_ticker_dict[cik] = ticker


def remove_master_index_file():
    """ Remove the old master index file.  Since we append to the file we need to start with a fresh slate """
    try:
        os.remove(f'{ev.output_folder}/master.idx')
        logger.info(f'Deleted {ev.output_folder}/master.idx file.')
    except FileNotFoundError:
        pass


def pad_string(string: str, padding_length=10, padding_character='0'):
    return string.rjust(padding_length, padding_character)


def price_rate_change(price1, price2):
    return (price1 - price2) / price2


def remove_filing_files():
    """ Remove previously downloaded files """
    logger.info(f'Started deleting all cleaned files from {ev.output_cleaned_files}.')
    file_list = os.listdir(ev.output_cleaned_files)
    for file in file_list:
        if file.endswith(".txt"):
            os.remove(f'{ev.output_cleaned_files}/{file}')
    logger.info(f'Finished deleting all cleaned files from {ev.output_cleaned_files}.')


def get_financial(data_dict):
    """
    This will pull financial data from Yahoo.  If the report is on a Friday then we will not
    process the data as too many things can happen over the weekend which could influence the stock.

    Best days to gather data is Monday, Tuesday, Wednesday (with no holidays).
    """
    global cik_to_ticker_dict

    cik = data_dict['cik']
    cik_log = pad_string(string=cik)

    try:
        ticker_symbol = cik_to_ticker_dict[cik]
        data_dict['ticker_symbol'] = ticker_symbol
        logger.debug(f'CIK: {cik_log} Ticker symbol is {ticker_symbol}.')
    except KeyError:
        logger.error(f'CIK: {cik_log} Could not find {cik} in ticker feed.')
        return {}

    accepted_date = datetime.strptime(data_dict['date_accepted'], '%Y-%m-%d %H:%M:%S')
    end_date = accepted_date + timedelta(days=3)
    logger.debug(f'CIK: {cik_log} Ticker: {ticker_symbol} Accepted date {accepted_date}.  End date is {end_date}')

    if not 16 <= accepted_date.hour <= 19:
        logging.info(f'CIK: {cik_log} Ticker: {ticker_symbol} 10-Q is outside time frame.  '
                     'Must be submitted between 4pm and 7pm.')
        return {}

    accepted_date = accepted_date.date()
    # Get the stock history between start and end date
    try:
        hist = yf.Ticker(ticker_symbol).history(start=accepted_date, end=end_date)
        if hist.empty:
            logger.error(f'CIK: {cik_log} Ticker: {ticker_symbol} Could not find a history in yFinance.')
            return {}
        logger.debug(f'CIK: {cik_log} Ticker: {ticker_symbol} Got yahoo finance history\r\n{hist}')
    except Exception as e:
        logging.error(f'CIK: {cik_log} Ticker: {ticker_symbol} yFinance encountered an error: {e}')
        return {}

    # See if there is any history for the next day
    next_business_day = accepted_date + timedelta(days=1)
    if next_business_day not in hist.index:
        logger.debug(f'CIK: {cik_log} Ticker: {ticker_symbol} No stock history for {next_business_day}.')
        return {}

    price1 = hist.loc[next_business_day]['Open']
    price2 = hist.loc[next_business_day]['Close']
    data_dict['prc_change'] = price_rate_change(price1, price2)
    logger.debug(f'CIK: {cik_log} Ticker: {ticker_symbol} Next business day {next_business_day} '
                 f'Open: {price1} Close: {price2}')

    # See if there is any history for following business day
    following_business_day = next_business_day + timedelta(days=1)
    if following_business_day not in hist.index:
        data_dict['error'] = f'No stock history for {following_business_day}'
        return data_dict

    price1 = hist.loc[next_business_day]['Open']
    price2 = hist.loc[following_business_day]['Open']
    logger.debug(f'CIK: {cik_log} Ticker: {ticker_symbol} Next business day {next_business_day} '
                 f'Open: {price1}.  Following business day Open: {price2}')
    data_dict['prc_change_t2'] = price_rate_change(price1, price2)
    return data_dict


def download_and_clean_filing(data_dict: dict):
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
                finance_data = get_financial(data_dict)
                logger.debug(f'CIK: {cik} Finished checking for financial data.')
                if finance_data:
                    if 'ix?' in filing_href:
                        filing_href = '/' + '/'.join(filing_href.split('/')[2:])

                    response = requests.request('GET', ev.sec_website + filing_href)
                    logger.debug(f'CIK: {cik} Started cleaning file.')
                    laundry = FilingCleaner(response.text, data_dict)
                    laundry.wash()
                    logger.debug(f'CIK: {cik} Finished cleaning file.')
                    return finance_data
                return {}
    return {}


def process_master_index():
    """
    Process the master.idx located in the output directory.  This was done previously (below).

    Process each line of the master.idx file.  This file in delimited by pipe symbol '|'
    For each line we extract the data then we download and clean the 10-Q.
    """
    build_dict_from_ticker()

    # Remove all the old cleaned filings
    remove_filing_files()

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
                'date_filed': date_filed
            })

    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
        logger.info(f'Started processing files. Number of CPU\'s: {multiprocessing.cpu_count()}')
        data = pool.imap(download_and_clean_filing, filings_to_download_and_clean, chunksize=100)
        logger.info('Finished processing files.')

        # Remove null entries in dictionary
        data = list(filter(None, data))

        logger.info('Started writing data files')
        with open(os.path.join(ev.output_data_files, 'finance.json'), 'w') as outfile:
            json.dump(data, outfile, indent=4)
        logger.info('Finished writing data file.')
    pool.close()
    pool.join()


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
