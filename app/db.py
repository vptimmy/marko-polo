from config import Environment
import os
import sqlite3
import logging

ev = Environment()
logger = logging.getLogger(ev.app_name)


def connect_to_db():
    db_location = os.path.join(ev.output_db, 'marko-polo.db')
    return sqlite3.connect(db_location, check_same_thread=False)


def insert_into_finance(finance_data):
    conn = connect_to_db()
    cursor = conn.cursor()

    prc_change2 = None
    if 'prc_change2' in finance_data:
        prc_change2 = finance_data['prc_change2']

    sql = '''INSERT INTO marko_finance 
                (cik, company_name, url, date_filed, date_accepted, ticker_symbol, file_name, prc_change, prc_change2)
                VALUES (?,?,?,?,?,?,?,?,?)
    '''
    cursor.execute(sql, (
        finance_data['cik'],
        finance_data['company_name'],
        finance_data['url'],
        finance_data['date_filed'],
        finance_data['date_accepted'],
        finance_data['ticker_symbol'],
        finance_data['file_name'],
        finance_data['prc_change'],
        prc_change2
    ))
    conn.commit()
    conn.close()


def truncate_finance():
    conn = connect_to_db()
    cursor = conn.cursor()
    sql = "DELETE FROM marko_finance"
    cursor.execute(sql)
    conn.commit()
    conn.close()


def create_finance_table():
    conn = connect_to_db()
    cursor = conn.cursor()

    sql = "SELECT name FROM sqlite_master WHERE type='table' and name='marko_finance'"
    cursor.execute(sql)
    results = cursor.fetchall()
    if len(results) <= 0:
        logger.info('Started creating sqlite table marko_finance')
        sql = '''CREATE TABLE IF NOT EXISTS marko_finance(
                        id integer PRIMARY KEY AUTOINCREMENT,
                        cik integer,
                        company_name text,
                        ticker_symbol text, 
                        date_filed text, 
                        date_accepted text,
                        prc_change text,
                        prc_change2 text,
                        file_name text,
                        url text,
                        difference_from_last_report text
                    )'''
        cursor.execute(sql)

        sql = 'CREATE INDEX indx_cik on marko_finance(cik)'
        conn.execute(sql)

        sql = 'CREATE INDEX indx_date_accepted on marko_finance(date_accepted)'
        conn.execute(sql)
        logger.info('Finished creating sqlite table marko_finance')
    conn.close()
