from robocorp.tasks import task

import pandas as pd
from pathlib import Path
from os import listdir, getcwd
import os 
import json
import requests
import re
import logging
import shutil

# Fallback to current dir if ROBOT_ARTIFACTS not set
OUTPUT_DIR = Path(os.environ.get('ROBOT_ARTIFACTS', '.'))

# Parameters
SEARCH_PHRASE = "technology"

# Number of months to consider
MONTHS_HORIZON = 3

# URL templates
NEWS_URL = "https://gothamist.com/search?q={search_term}"

# Delimiter for CSV file
DELIMITER = '|'

class NewsScraper:
    def __init__(self, output_dir, delimiter=DELIMITER):
        self.output_dir = Path(output_dir)
        self.delimiter = delimiter
        self.news_url = "https://gothamist.com/search?q={search_phrase}"
        self.json_responses_dir = 'json_responses'
        self.search_results_dir = 'search_results'
        self.output_folder = 'output'

    def search_and_save(self, search_phrase):
        """
        Search for a term using a URL template and save the search results page.
        """
        search_url = self.news_url.format(search_phrase=search_phrase)
        logging.info(f"Searching for '{search_phrase}' using {search_url}")

        os.makedirs(self.search_results_dir, exist_ok=True)
        domain = search_url.split('/')[2]

        try:
            response = requests.get(search_url)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching search results: {e}")
            return

        filename=f"{domain}_search_{search_phrase}.html"
        output_filepath = os.path.join(self.search_results_dir, filename)
        with open(output_filepath, 'wb') as outfile:
            outfile.write(response.content)
        
        where_str=f"'{search_phrase}' from {search_url}"
        log_msg=f"Fetched search results for {where_str} and saved as {output_filepath}"
        logging.info(log_msg)
        return output_filepath

    def download_json_responses(self, input_file):
        """
        Download JSON responses from URLs in the input file.
        """
        pattern = r'https://api-prod.gothamist.com/api/v2/pages/[0-9]{4,}'
        if not os.path.isfile(input_file):
            logging.error(f"Input file '{input_file}' not found.")
            return

        os.makedirs(self.json_responses_dir, exist_ok=True)
        with open(input_file, 'r') as file:
            links = re.findall(pattern, file.read())

        for link in links:
            news_number = re.search(r'[0-9]+$', link).group()
            filename = f"news_{news_number}.json"
            output_file = os.path.join(self.json_responses_dir, filename)
            response = requests.get(link)

            if response.status_code == 200:
                with open(output_file, 'wb') as outfile:
                    outfile.write(response.content)
                logging.info(f"Downloaded {link} to {output_file}")
            else:
                logging.error(f"Failed to download {link}. Status code: {response.status_code}")

        what_str=f"{input_file} to {self.json_responses_dir}/news_*.json"
        log_msg=f"Downloaded JSON responses from links in {what_str}"
        logging.info(log_msg)

    def extract_data(self, search_phrase):
        """
        Extract data from JSON files in the specified folder.
        """
        filenames = listdir(self.json_responses_dir)
        filenames = [f for f in filenames if f.endswith('.json')]

        data = {
            'id': [], 'title': [], 'date': [], 'description': [],
            'picture_filename': [], 'search_phrase_count': [], 'contains_money': []
        }

        for filename in filenames:
            file_path = f'{self.json_responses_dir}/{filename}'
            try:
                with open(file_path, 'r') as file:
                    json_data = json.load(file)
                    id_ = filename.split('.')[0].split('_')[-1]
                    title = json_data['title']
                    date = json_data['publication_date']
                    description = json_data.get('description', '')
                    picture_filename = ''
                    for image_data in json_data.get('lead_asset', []):
                        if image_data['type'] == 'lead_image':
                            picture_filename = image_data['value']['image']['file']
                            break

                    search_phrases = [search_phrase]
                    title_search_count = sum(1 for phrase in search_phrases if phrase in title)
                    description_search_count = sum(1 for phrase in search_phrases if phrase in description)
                    money_pattern = r'\$[\d,]+(\.\d+)?|\d+\s(dollars|USD)'
                    title_has_money = bool(re.search(money_pattern, title))
                    description_has_money = bool(re.search(money_pattern, description))

                    data['id'].append(id_)
                    data['title'].append(title)
                    data['date'].append(date)
                    data['description'].append(description)
                    data['picture_filename'].append(picture_filename)
                    data['search_phrase_count'].append(title_search_count + description_search_count)
                    data['contains_money'].append(title_has_money or description_has_money)
            except Exception as e:
                logging.error(f'Error processing file {file_path}: {e}')

        df = pd.DataFrame(data)
        return df

    def generate_month_mask(self, series_, months_horizon):
        """
        Generate a boolean mask to filter dates within a specified number of months.
        """
        from datetime import datetime
        import pytz

        num_months = max(0, months_horizon - 1)

        if not pd.api.types.is_datetime64_any_dtype(series_):
            series_ = pd.to_datetime(series_, utc=True, format='mixed')
        elif series_.dtype != 'datetime64[ns, UTC]':
            series_ = series_.dt.tz_localize('UTC')

        current_date = datetime.now(pytz.utc)
        start_date = current_date - pd.DateOffset(months=num_months)
        mask = (series_ >= start_date) & (series_ <= current_date)

        return mask

    def save_data(self, df, search_phrase, months_horizon):
        """
        Save the extracted data to a CSV file.
        """
        date_ = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f'output_{search_phrase}_m{months_horizon}_d{date_}.csv'
        os.makedirs(self.output_folder, exist_ok=True)
        to_save = os.path.join(getcwd(), self.output_folder, output_filename)

        filter_mask = self.generate_month_mask(df['date'], months_horizon)
        df_filtered = df[filter_mask]
        df_filtered.to_csv(to_save, index=False, sep=self.delimiter)
        logging.info('Data saved to CSV')
        
    def scrap_news(self, search_phrase: str, months_horizon: int):
        filepath = self.search_and_save(search_phrase)

        if filepath:
            self.download_json_responses(filepath)
            shutil.rmtree(self.search_results_dir)

        filenames = listdir(self.json_responses_dir)
        if not filenames:
            logging.info('No JSON responses to process. Exiting...')
        else:
            df = self.extract_data(search_phrase)
            shutil.rmtree(self.json_responses_dir)
            self.save_data(df, search_phrase, months_horizon)
            logging.info('Done!')

@task
def solve_challenge():
    """
    Solve the RPA challenge for scraping news data from Reuters.
    """
    scraper = NewsScraper(output_dir='.')
    scraper.scrap_news(SEARCH_PHRASE, MONTHS_HORIZON)

