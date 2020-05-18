from datetime import datetime, timedelta
import yfinance as yf
import logging
import requests
import os
from config import Environment

ev = Environment()
logger = logging.getLogger(ev.app_name)


def pad_string(string: str, padding_length=10, padding_character='0'):
    return string.rjust(padding_length, padding_character)


def price_rate_change(price1, price2):
    return round((price1 - price2) / price2, 5)


def generate_cik_to_ticker_dict():
    """
    Download the ticker.txt file from SEC.
    """
    cik_to_ticker_dict = dict()
    logger.info(f'Getting ticker / cik map from {ev.sec_ticker_url}.')
    ticker = requests.get(ev.sec_ticker_url)
    lines = ticker.text.splitlines()
    for line in lines:
        (ticker_symbol, cik) = line.split('\t')
        if cik in cik_to_ticker_dict:
            logger.debug(f'CIK {cik} is already mapped to {cik_to_ticker_dict[cik]}.  Not mapping to {ticker_symbol}')
        else:
            cik_to_ticker_dict[cik] = ticker_symbol

    with open(os.path.join(ev.dir_path, 'input', 'cik_to_ticker.txt')) as cik_input:
        for line in cik_input:
            if not line.startswith('#') and len(line) > 5:
                cik, ticker_symbol = line.strip().split(' ')
                if cik and ticker_symbol:
                    # Allow custom ticker to override SEC one.  SEC does not seem up to date.
                    cik_to_ticker_dict[cik] = ticker_symbol
    return cik_to_ticker_dict


def get_financial(data_dict, cik_to_ticker_dict):
    """
    This will pull financial data from Yahoo.  If the report is on a Friday then we will not
    process the data as too many things can happen over the weekend which could influence the stock.

    Best days to gather data is Monday, Tuesday, Wednesday (with no holidays).
    """

    cik = data_dict['cik']
    cik_log = pad_string(string=cik)

    try:
        ticker_symbol = cik_to_ticker_dict[cik]
        data_dict['ticker_symbol'] = ticker_symbol
        logger.debug(f'CIK: {cik_log} Ticker symbol is {ticker_symbol}.')
    except KeyError:
        logger.error(f'CIK: {cik_log} Could not find {cik} in ticker feed.')
        return data_dict

    accepted_date = datetime.strptime(data_dict['date_accepted'], '%Y-%m-%d %H:%M:%S')
    end_date = accepted_date + timedelta(days=3)
    logger.debug(f'CIK: {cik_log} Ticker: {ticker_symbol} Accepted date {accepted_date}.  End date is {end_date}')

    if not (16 <= accepted_date.hour <= 19):
        logging.info(f'CIK: {cik_log} Ticker: {ticker_symbol} 10-Q is outside time frame.  '
                     'Must be submitted between 4pm and 7pm.')
        return data_dict

    accepted_date = accepted_date.date()
    # Get the stock history between start and end date
    try:
        hist = yf.Ticker(ticker_symbol).history(start=accepted_date, end=end_date)
        if hist.empty:
            logger.error(f'CIK: {cik_log} Ticker: {ticker_symbol} Could not find a history in yFinance.')
            return data_dict
        logger.debug(f'CIK: {cik_log} Ticker: {ticker_symbol} Got yahoo finance history\r\n{hist}')
    except Exception as e:
        logging.error(f'CIK: {cik_log} Ticker: {ticker_symbol} yFinance encountered an error: {e}')
        return data_dict

    # See if there is any history for the next day
    next_business_day = accepted_date + timedelta(days=1)
    if next_business_day not in hist.index:
        logger.debug(f'CIK: {cik_log} Ticker: {ticker_symbol} No stock history for {next_business_day}.')
        return data_dict

    price1 = hist.loc[next_business_day]['Open']
    price2 = hist.loc[next_business_day]['Close']
    data_dict['prc_change'] = price_rate_change(price2, price1)
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
    data_dict['prc_change2'] = price_rate_change(price2, price1)
    return data_dict
