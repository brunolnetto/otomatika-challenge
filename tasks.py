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

# Adjust as needed
NUMBER_OF_MONTHS = 1

# URL templates
NEWS_URL = "https://gothamist.com/search?q={search_term}"
    

@task
def solve_challenge():
    """
    Solve the RPA challenge for scraping news data from Reuters
    """
    logging.info(f'Searching for {SEARCH_PHRASE} on {NEWS_URL} and saving the search results')
    filepath = search_and_save(NEWS_URL, SEARCH_PHRASE, 'search_results')

    if filepath:
        # Define the pattern to match URLs
        pattern = r'https://api-prod.gothamist.com/api/v2/pages/[0-9]{4,}'

        logging.info('Downloading JSON responses')
        download_json_responses(filepath, pattern, 'json_responses')

    shutil.rmtree('search_results')

    filenames = listdir('json_responses')

    if not filenames:
        logging.info('No JSON responses to process. Exiting...')
        exit()
    else: 
        # Extract data from JSON responses
        logging.info('Extracting data')
        df = extract_data('json_responses', [SEARCH_PHRASE])

        shutil.rmtree('json_responses')

        # Save the extracted data to a CSV file
        logging.info(f"Saving extracted data to 'output.csv'")
        output_folder='output'
        output_filename='output.csv'
        os.makedirs(output_folder, exist_ok=True)
        to_save=os.path.join(getcwd(), output_folder, output_filename)

        df.to_csv(to_save, index=False)
        logging.info('Done!')

def search_and_save(
    url_template: str, search_term: str, output_dir: str
):
    # Replace the placeholder with the search term
    search_url = url_template.format(search_term=search_term)
    logging.info(f"Searching for '{search_term}' using {search_url}")

    # Create directory to save the search results pages
    os.makedirs(output_dir, exist_ok=True)

    # Extract the domain name to use as part of the filename
    domain = search_url.split('/')[2]

    # Fetch the search results page
    try:
        response = requests.get(search_url)

        # Raise error for bad responses (4xx or 5xx)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.info(f"Error fetching search results: {e}")
        return

    # Save the search results page to the output directory
    output_filepath = os.path.join(output_dir, f"{domain}_search_{search_term}.html")

    with open(output_filepath, 'wb') as outfile:
        outfile.write(response.content)

    info_msg=f"Fetched search results for '{search_term}' from {search_url} and saved as {output_filepath}"
    logging.info(info_msg)

    return output_filepath

def download_json_responses(
    input_file: str, pattern: str, output_dir: str
):
    # Check if the input file exists
    if not os.path.isfile(input_file):
        print(f"Input file '{input_file}' not found.")
        return

    output_file_prefix = 'news'

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Read input file and find all URLs matching the pattern
    with open(input_file, 'r') as file:
        links = re.findall(pattern, file.read())

    # Download each link using requests library
    for link in links:
        # Extract the news number from the link
        news_number = re.search(r'[0-9]+$', link).group()

        # Construct the output file path
        filename = f"{output_file_prefix}_{news_number}.json"
        output_file = os.path.join(output_dir, filename)

        # Perform GET request to download JSON data
        response = requests.get(link)

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Save the JSON response to file
            with open(output_file, 'wb') as outfile:
                outfile.write(response.content)

            logging.info(f"Downloaded {link} to {output_file}")
        else:
            logging.error(f"Failed to download {link}. Status code: {response.status_code}")

    logging.info(f"Downloaded JSON responses from links in {input_file} to {output_dir}/{output_file_prefix}_*.json")


def extract_data(source_folder, search_phrases):
    # Assuming 'data' contains the JSON data you provided earlier
    filenames = listdir(source_folder)
    filenames = [f for f in filenames if f.endswith('.json')]

    # Initialize lists to store extracted data
    ids = []
    titles = []
    dates = []
    descriptions = []
    picture_filenames = []
    search_phrase_counts = []
    contains_money = []

    for filename in filenames:
        file_path=f'{source_folder}/{filename}'
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)

                # Extract basic fields
                id_ = filename.split('.')[0].split('_')[-1]
                title = data['title']
                date = data['publication_date']
                description = data.get('description', '')
                picture_filename = ''
                for image_data in data.get('lead_asset', []):
                    if image_data['type'] == 'lead_image':    
                        picture_filename = image_data['value']['image']['file']
                        break 
                
                # Count search phrases in title and description
                title_search_count = sum(1 for phrase in search_phrases if phrase in title)
                description_search_count = sum(1 for phrase in search_phrases if phrase in description)

                # Check if title or description contains any money mention
                # Regular expression pattern to detect money formats
                money_pattern = r'\$[\d,]+(\.\d+)?|\d+\s(dollars|USD)'
                
                title_has_money = bool(re.search(money_pattern, title))
                description_has_money = bool(re.search(money_pattern, description))

                # Store extracted data in lists
                ids.append(id_)
                titles.append(title)
                dates.append(date)
                descriptions.append(description)
                picture_filenames.append(picture_filename)
                search_phrase_counts.append(title_search_count + description_search_count)
                contains_money.append(title_has_money or description_has_money)

        except Exception as e:
            print(f'Error processing file {file_path}: {e}')

    # Create a Pandas DataFrame
    df_data={
        'id': ids,
        'title': titles,
        'date': dates,
        'description': descriptions,
        'picture_filename': picture_filenames,
        'search_phrase_count': search_phrase_counts,
        'contains_money': contains_money
    }
    df = pd.DataFrame(df_data)

    return df