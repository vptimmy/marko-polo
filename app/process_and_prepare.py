from config import Environment
import json
import os
import logging
from datetime import date

ev = Environment()
logger = logging.getLogger(ev.app_name)


class ProcessAndPrepare:
    def __init__(self):
        with open(os.path.join(ev.output_folder, 'data', 'finance.json')) as json_file:
            self.finance_data = json.load(json_file)


