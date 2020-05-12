import os
import multiprocessing
import numpy as np
import logging
import zipfile
import urllib.request
import urllib.parse
from urllib.error import HTTPError

import config
from laundry import FilingCleaner

from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import yfinance as yf

logger = logging.getLogger(config.app_name)

cik_to_ticker_dict = dict()


def build_dict_from_ticker():
    cik_ticker_dict = dict()
    logger.info(f'Getting ticker / cik map from {config.sec_ticker_url}.')
    ticker = requests.get(config.sec_ticker_url)
    lines = ticker.text.splitlines()
    for line in lines:
        (ticker_symbol, cik) = line.split('\t')
        cik_ticker_dict[cik] = ticker_symbol
    return cik_ticker_dict


def get_financial(data_dict):
    global cik_to_ticker_dict
    finance_dict = dict()

    cik = data_dict['cik']

    try:
        ticker_symbol = cik_to_ticker_dict[cik]
        logger.debug(f'ticker symbol for cik {cik} is {ticker_symbol}.')
    except KeyError:
        logger.error(f'Could not find {cik} in ticker feed.')
        return finance_dict

    approved_date = datetime.strptime(data_dict['date'], '%Y-%m-%d %H:%M:%S')
    end_date = approved_date + timedelta(days=3)

    if not (16 <= approved_date.hour <= 19):
        logging.info('outside hours')
        return finance_dict

    # Do not include the weekends dates
    work_days = np.busday_count(approved_date, end_date)
    while work_days < 3:
        end_date = end_date + timedelta(days=1)
        work_days = np.busday_count(approved_date, end_date)

    # Get the stock history between start and end date
    try:
        hist = yf.Ticker(ticker_symbol).history(start=approved_date, end=end_date)
        logger.debug(f'Got yahoo finance history {hist}')
    except Exception as e:
        logging.error(f'yFinance encountered an error: {e}')
        return finance_dict

    next_business_day = approved_date + timedelta(days=1)
    if next_business_day.weekday() == 6:
        next_business_day = approved_date + timedelta(days=2)
    elif next_business_day.weekday() == 7:
        next_business_day = approved_date + timedelta(days=1)

    if next_business_day not in hist.index:
        logger.debug(f'Could not find a history for {ticker_symbol} on {next_business_day}.')
        return finance_dict

    price1 = hist.loc[next_business_day]['Open']
    price2 = hist.loc[next_business_day]['Close']
    finance_dict['prc_change'] = price_rate_change(price1, price2)

    following_business_day = next_business_day + timedelta(days=1)
    if following_business_day.weekday() == 6:
        following_business_day = following_business_day + timedelta(days=2)
    elif following_business_day.weekday() == 7:
        following_business_day = following_business_day + timedelta(days=1)

    if following_business_day in hist.index:
        price1 = hist.loc[next_business_day]['Open']
        price2 = hist.loc[following_business_day]['Open']
        finance_dict['prc_change_t2'] = price_rate_change(price1, price2)

    return finance_dict


def price_rate_change(price1, price2):
    return (price1 - price2) / price2


def remove_filing_files():
    """ Remove previously downloaded files """
    file_list = os.listdir(config.output_folder)
    for file in file_list:
        if file.endswith(".txt"):
            os.remove(f'{config.output_folder}/{file}')


def remove_master_index_file():
    """ Remove the old master index file.  Since we append to the file we need to start with a fresh slate """
    try:
        os.remove(f'{config.output_folder}/master.idx')
    except FileNotFoundError:
        pass


def download_and_clean_filing(data_dict):
    uri = data_dict['uri']

    logger.info(f'Processing {uri}')
    url = f'{config.sec_website}/Archives/{uri}'
    response = requests.get(url)

    soup = BeautifulSoup(response.content.decode('utf-8'), "lxml")
    documents = soup.find('table', {'class': 'tableFile', 'summary': 'Document Format Files'})
    if documents:
        for tr in documents.find_all('tr'):
            td = tr.find_all('td')
            if len(td) >= 4 and td[3].text == config.sec_form_type:
                # We found the report.
                filing_url = td[2].find('a', href=True)
                filing_href = filing_url['href']
                data_dict['date'] = soup.find('div', attrs={'class': 'infoHead'}, text='Accepted')\
                                        .findNext('div', {'class': 'info'}).text

                if 'ix?' in filing_href:
                    filing_href = '/' + '/'.join(filing_href.split('/')[2:])

                response = requests.request('GET', config.sec_website + filing_href)

                laundry = FilingCleaner(response.text, data_dict)
                laundry.wash()
                laundry.fold()
                break


def process_master_index():
    """
    Now we process our master index file
    1) Loop through each filing and make sure it is a 10-Q filing.
    2) If it is a Q-10 then add it to a list
    3) Download and clean all the items in the list
    4) Be sure to set your CPU number_of_pools.  View the README to learn more.
    """
    global cik_to_ticker_dict

    # Remove all the old cleaned filings
    remove_filing_files()

    # Created by download_master_zip function below.
    master_index = open(f'{config.output_folder}/master.idx')
    lines = master_index.read().splitlines()
    master_index.close()

    filings_to_download_and_clean = list()
    cik_to_ticker_dict = build_dict_from_ticker()

    for line in lines:
        (cik, company_name, form_type, date_filed, file_name) = line.split('|')

        if form_type == config.sec_form_type:
            filings_to_download_and_clean.append({
                'uri': file_name.replace(".txt", "-index.html"),
                'cik': cik
            })

    with multiprocessing.Pool(processes=int(config.number_of_pools)) as pool:
        results = [pool.map_async(download_and_clean_filing, filings_to_download_and_clean)]
        [p.get() for p in results]
    pool.close()
    pool.join()


def append_master_index(zip_file):
    """ Get the master.idx file from the zip file """
    with zipfile.ZipFile(zip_file) as edgar_file:
        logger.debug(f'Extracting {zip_file}.')
        zip_data = edgar_file.read('master.idx').splitlines()
        with open(f'{config.output_folder}/master.idx', "a") as master_index:
            for line in zip_data:
                # byte -> string
                line = line.decode()

                # If this is a 10-Q filing then add it to the master index file
                if '|' in line and config.sec_form_type in line and not line.startswith('CIK'):
                    master_index.write(f'{line}\n')


def download_master_zip():
    """ Retrieve quarter master.zip file from sec website for each given year """

    remove_master_index_file()

    logger.info(f'Started retrieving edgar master zip files since {config.sec_beginning_year}.')
    year = config.sec_beginning_year
    while year <= datetime.today().year:
        for quarter in ['QTR1', 'QTR2', 'QTR3', 'QTR4']:
            try:
                # Download and save it
                zip_file = f'{config.sec_website}/Archives/edgar/full-index/{year}/{quarter}/master.zip'
                save_to = f'{config.output_folder}/{year}{quarter}.zip'

                logger.info(f'Started processing and retrieving {year} {quarter} master.zip.')
                logger.debug(f'Started downloading {zip_file}.')
                urllib.request.urlretrieve(zip_file, save_to)
                logger.debug(f'Finished downloading {zip_file}.')

                # Extract it
                logger.debug(f'Started extracting master.zip file and appending to master index')
                append_master_index(save_to)
                logger.debug(f'Finished extracting master.zip file and appending to master index')

                # Remove the old zip file
                os.remove(save_to)
                logger.info(f'Finished processing and retrieving master.zip.')

            except HTTPError as http_error:
                # The file does not exist.  No worries.  Probably a quarter in the future.
                logger.error(f'An error occurred while trying to retrieve the {year}{quarter} master.zip file. '
                             f'Error: {http_error}')
        year += 1
    logger.info(f'Finished retrieving edgar master zip files.')
