import os

dir_path = os.path.dirname(os.path.realpath(__file__))

ticker = dict()
app_name = 'marko-polo'
logging_level = 'DEBUG'
logging_format = '%(asctime)s %(levelname)s %(filename)s %(lineno)s %(message)s'
logging_date_format = '%H:%M:%S'
number_of_pools = 8

output_folder = os.path.join(dir_path, 'output')
output_cleaned_files = os.path.join(dir_path, output_folder, 'cleaned_files')
output_log_files = os.path.join(dir_path, output_folder, "logs")
output_data_files = os.path.join(dir_path, output_folder, "data")

sec_website = 'https://www.sec.gov'
sec_ticker_url = sec_website + '/include/ticker.txt'
sec_ticker_dict = dict()
sec_beginning_year = 2019
sec_form_type = '10-Q'