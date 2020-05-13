import os
from dotenv import load_dotenv


class Environment:
    def __init__(self):
        # application information
        self.app_name = 'marko-polo'
        self.logging_level = 'INFO'
        self.logging_format = '%(asctime)s %(levelname)5s %(message)s File: %(filename)s Line: %(lineno)s'
        self.logging_date_format = '%H:%M:%S'
        self.number_of_pools = 8

        # output folders
        self.dir_path = os.path.dirname(os.path.realpath(__file__))
        self.output_folder = os.path.join(self.dir_path, 'output')
        self.output_cleaned_files = os.path.join(self.output_folder, 'cleaned_files')
        self.output_log_files = os.path.join(self.output_folder, "logs")
        self.output_data_files = os.path.join(self.output_folder, "data")
        self.output_db = os.path.join(self.output_folder, "db")

        # sec stuff
        self.sec_website = 'https://www.sec.gov'
        self.sec_ticker_url = self.sec_website + '/include/ticker.txt'
        self.sec_ticker_dict = dict()
        self.sec_analyze_since_fy = 2020
        self.sec_analyze_quarter = None
        self.sec_form_type = '10-Q'

        # where to start
        self.app_do_all = True
        self.app_parse_finance = False

        # load custom .env files from .env files.
        load_dotenv()
        for env, env_value in os.environ.items():
            name = env.lower()
            self.__setattr__(name, env_value)
