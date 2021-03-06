from bs4 import BeautifulSoup
from config import Environment
import html
import re
import logging
import os

ev = Environment()
logger = logging.getLogger(ev.app_name)


class FilingCleaner:
    def __init__(self, text, data_dict):
        self.stop_words = set(line.strip().lower() for line in open('input/stopwords.txt'))
        self.soup = BeautifulSoup(html.unescape(re.sub(r'\s+', ' ', text)), "lxml")
        self.data_dict = data_dict
        self.text = ''

    def remove_numerical_tables(self):
        def get_digit_percentage(table):
            if len(table) > 0.0:
                numbers = sum([char.isdigit() for char in table])
                length = len(table)
                return numbers / length
            else:
                return 1

        def contains_bg_color(table):
            for row in table.find_all('tr'):
                colored_bg = 'background-color' in str(row) or 'bgcolor' in str(row)
                if colored_bg:
                    return True
            return False

        [x.extract() for x in self.soup.find_all('table') if contains_bg_color(x)]
        [x.extract() for x in self.soup.find_all('table') if get_digit_percentage(x.get_text()) > 0.15]

    def wash(self):
        logger.debug(f'CIK: {self.data_dict["cik"]}. Started cleaning file.')

        # Remove xml xbrli and local href
        [x.extract() for x in self.soup.find_all(re.compile("^xbrli:"))]
        [x.extract() for x in self.soup.find_all('a', href=True) if len(x['href']) > 0 and x['href'][0] == '#']

        # Remove and colored and numeric tables and basic html tags
        self.remove_numerical_tables()
        [x.unwrap() for x in self.soup.find_all(['span', 'font', 'b', 'i', 'u', 'strong', 'img'])]

        # clean up
        self.soup.smooth()

        text = self.soup.get_text('\n', strip=True)
        pattern = re.compile(r'\b(' + r'|'.join(self.stop_words) + r')\b\s*', re.IGNORECASE)
        text = pattern.sub('', text)
        pattern = re.compile('\s[^a-zA-Z\s]+?(?=(\.*\s))')
        text = pattern.sub('', text)

        self.text = '\n'.join(
            filter(lambda line: len(line) > 0 and (sum(i.isalpha() for i in line) / len(line) > .5), text.splitlines()))

        file_date, _ = self.data_dict['date_accepted'].split(' ')
        file_name = f'{self.data_dict["cik"]}-{file_date}.txt'
        with open(os.path.join(ev.output_cleaned_files, file_name), 'w') as file:
            file.write(self.text)

        logger.debug(f'CIK: {self.data_dict["cik"]}. Finished cleaning file {file_name}.')
        return file_name
