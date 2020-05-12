from bs4 import BeautifulSoup
import config
import html
import re
import logging

logger = logging.getLogger(config.app_name)


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
        logger.info('Started washing.')

        # Remove xml xbrli
        [x.extract() for x in self.soup.find_all(re.compile("^xbrli:"))]

        # Remove local href
        [x.extract() for x in self.soup.find_all('a', href=True) if len(x['href']) > 0 and x['href'][0] == '#']

        # Remove and colored and numeric tables
        self.remove_numerical_tables()

        # Get rid of everything with basic html
        [x.unwrap() for x in self.soup.find_all(['span', 'font', 'b', 'i', 'u', 'strong', 'img'])]

        self.soup.smooth()

        text = self.soup.get_text('\n', strip=True)
        pattern = re.compile(r'\b(' + r'|'.join(self.stop_words) + r')\b\s*', re.IGNORECASE)
        text = pattern.sub('', text)
        pattern = re.compile('\s[^a-zA-Z\s]+?(?=(\.*\s))')
        text = pattern.sub('', text)

        self.text = '\n'.join(
            filter(lambda line: len(line) > 0 and (sum(i.isalpha() for i in line) / len(line) > .5), text.splitlines()))

        file_name = f'{config.output_cleaned_files}/{self.data_dict["cik"]}-{self.data_dict["date_accepted"]}.txt'
        with open(file_name, 'w') as file:
            file.write(self.text)
        logger.info(f'Finished washing {file_name}.')
