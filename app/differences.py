import os
import db
from datetime import datetime
import logging
from config import Environment
from fuzzywuzzy import process, fuzz
import nltk
import multiprocessing

ev = Environment()
logger = logging.getLogger(ev.app_name)

# nltk punkt sentence trainer.
nltk.download('punkt')
detector = nltk.data.load('tokenizers/punkt/english.pickle')


def create_diff(data_dict):
    current_report_file = data_dict['current_file']
    last_report_file = data_dict['old_file']
    record_id = data_dict['id']

    with open(os.path.join(ev.output_cleaned_files, current_report_file)) as current_report:
        current_report_list = current_report.read().splitlines()

    with open(os.path.join(ev.output_cleaned_files, last_report_file)) as current_report:
        last_report_list = current_report.read().splitlines()

    # remove exact lines from each other
    current_report_dedup_list = [line for line in current_report_list if line not in last_report_list]
    last_report_dedup_list = [line for line in last_report_list if line not in current_report_list]

    # list of sentences in each file
    current_report_sentences = list(detector.tokenize(' '.join(current_report_dedup_list).strip()))
    last_report_sentences = list(detector.tokenize(' '.join(last_report_dedup_list).strip()))

    # for each new sentence in the report look to see if we have a fuzzy match of 85% of better against any
    # sentence in the older report.  If not consider it a new sentence.
    new_sentences = list()
    for sentence in current_report_sentences:
        match = process.extractOne(sentence, last_report_sentences, score_cutoff=85, scorer=fuzz.QRatio)
        if match is None:
            new_sentences.append(sentence)

    if new_sentences:
        new_sentence = '\n'.join(new_sentences)

        conn = db.connect_to_db()
        cursor = conn.cursor()
        sql = 'UPDATE marko_finance SET difference_from_last_report=? WHERE id=?'
        cursor.execute(sql, (new_sentence, record_id))
        conn.commit()
        conn.close()
        logger.info(f'Difference logged between {current_report_file} and {last_report_file}')
    return


def get_differences():
    logger.info(f'Started processing differences')

    conn = db.connect_to_db()
    sql = '''SELECT 
                id, 
                cik, 
                file_name, 
                date_accepted, 
                company_name 
            FROM 
                marko_finance 
            WHERE 
                difference_from_last_report IS NULL 
            ORDER BY cik, date_accepted'''
    cursor = conn.cursor()
    cursor.execute(sql)
    results = cursor.fetchall()

    old_cik = None
    old_date = None
    old_filename = None

    find_differences_list = list()
    for record in results:
        (record_id, cik, filename, date_accepted, company_name) = record
        converted_date = datetime.strptime(date_accepted, '%Y-%m-%d %H:%M:%S')

        if cik == old_cik:
            week_difference = (converted_date - old_date).days / 7
            if 9 <= week_difference <= 17:
                find_differences_list.append({
                    'id': record_id,
                    'cik': cik,
                    'company_name': company_name,
                    'current_file': filename,
                    'old_file': old_filename
                })
        old_cik = cik
        old_date = converted_date
        old_filename = filename
    conn.close()

    with multiprocessing.Pool(processes=ev.number_of_cores) as pool:
        pool.map(create_diff, find_differences_list)
    pool.close()
    pool.join()

    logger.info(f'Finished processing differences')

