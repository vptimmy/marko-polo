import os
import multiprocessing
from dotenv import load_dotenv
from distutils import util


class Environment:
    def __init__(self):
        # application information
        self.app_name = 'marko-polo'
        self.logging_level = 'DEBUG'
        self.logging_format = '%(asctime)s %(levelname)5s %(message)s File: %(filename)s Line: %(lineno)s'
        self.logging_date_format = '%H:%M:%S'
        self.number_of_cores = None

        # output folders
        self.dir_path = os.path.dirname(os.path.realpath(__file__))
        self.output_folder = os.path.join(self.dir_path, 'output')
        self.output_cleaned_files = os.path.join(self.output_folder, 'cleaned_files')
        self.output_log_files = os.path.join(self.output_folder, "logs")
        self.output_db = os.path.join(self.output_folder, "db")

        # sec stuff
        self.sec_website = 'https://www.sec.gov'
        self.sec_ticker_url = self.sec_website + '/include/ticker.txt'
        self.sec_analyze_since_fy = 2020
        self.sec_analyze_quarter = None
        self.sec_form_type = '10-Q'

        # where to start
        self.app_get_differences = '0'
        self.app_create_report = '0'

        # load custom .env files from .env files.
        load_dotenv()
        for env, env_value in os.environ.items():
            name = env.lower()
            self.__setattr__(name, env_value)

        # Let the limit / set the number of cores to be used.
        if self.number_of_cores:
            self.number_of_cores = int(self.number_of_cores)

            # Make sure they did not add more cores then possible.
            if self.number_of_cores > multiprocessing.cpu_count():
                self.number_of_cores = multiprocessing.cpu_count()
        else:
            # Assign current cpu count
            self.number_of_cores = multiprocessing.cpu_count()

        self.app_get_differences = bool(util.strtobool(self.app_get_differences))
        self.app_create_report = bool(util.strtobool(self.app_create_report))
