from robocorp import browser 
from robocorp.tasks import task

from RPA.Excel.Files import Files as Excel
from RPA.Robocorp.WorkItems import WorkItems

from pathlib import Path
import os
import requests
import re
import logging

FILE_NAME = "reuters_news.xlsx"

# Fallback to current dir if ROBOT_ARTIFACTS not set
OUTPUT_DIR = Path(os.environ.get('ROBOT_ARTIFACTS', '.'))

# Parameters
SEARCH_PHRASE = "technology"

# Example category
NEWS_CATEGORY = "technology"

# Adjust as needed
NUMBER_OF_MONTHS = 1

NEWS_URL="https://www.latimes.com/search?q=abc&p=2"

# https://apnews.com/search?q=abc&p=2            : OK
# https://gothamist.com/search?q=abc             : OK
# https://www.latimes.com/search?q=abc&p=2       : OK
# https://search.yahoo.com/search?p=abc          : Intricated news page 
# https://www.aljazeera.com/search/abc           : captcha-protected
# https://www.reuters.com/site-search/?query=abc : captcha-protected


@task
def solve_challenge():
    """
    Solve the RPA challenge for scraping news data from Reuters
    """
    browser.configure(
        browser_engine="chromium",
        screenshot="only-on-failure",
        headless=True,
    )
    try:
        page = browser.goto(NEWS_URL)

        # Perform search
        perform_search(page, SEARCH_PHRASE)

        # Filter news articles by category and time
        filter_news(page, NEWS_CATEGORY, NUMBER_OF_MONTHS)

        # Extract news data
        news_data = extract_news_data(page)
        
        news_len = len(news_data)
        
        # Save data to Excel
        save_data_to_excel(news_data, OUTPUT_DIR / FILE_NAME)

    finally:
        print(f'We found {news_len} news. Check the output file {FILE_NAME} in {OUTPUT_DIR}')
        

def perform_search(page, phrase):
    """
    Perform a search on news website with the given search phrase
    """
    search_box = page.query_selector('input[aria-label="Search Reuters"]')
    search_box.fill(phrase)
    search_box.press('Enter')

def filter_news(page, category, months):
    """
    Filter news by category and time
    """
    # Filtering logic can be implemented based on the website's structure
    # As an example, navigating to a specific category
    if category:
        category_link = page.query_selector(f'css=a[href*="{category}"]')
        if category_link:
            category_link.click()


def extract_news_data(page):
    """
    Extract news data from the search results
    """
    news_data = []

    # Adjust based on actual website structure
    articles = page.query_selector_all('article')

    for article in articles:
        query_selector_map=lambda tag: article.query_selector(tag)
        
        title = '' if not query_selector_map('h3') else query_selector_map('h3').inner_text()
        date = '' if not query_selector_map('time') else query_selector_map('time').inner_text()
        description = '' if query_selector_map('p') else query_selector_map('p').inner_text()
        image = '' if not query_selector_map('img') else query_selector_map('img').get_attribute('src')

        # Count occurrences of the search phrase in title and description
        lower_search_phrase = SEARCH_PHRASE.lower()
        count_item_map = lambda x: x.lower().count(lower_search_phrase)
        phrase_count = count_item_map(title) + count_item_map(description)

        # Check for monetary values
        money_pattern = r"\$\d+[\d,.]*|\d+ dollars|\d+ USD"
        title_has_money=bool(re.search(money_pattern, title))
        description_has_money=bool(re.search(money_pattern, description))
        contains_money = title_has_money or description_has_money

        new_data={
            'Title': title,
            'Date': date,
            'Description': description,
            'Image Filename': download_image(image, OUTPUT_DIR) if image != "N/A" else "N/A",
            'Phrase Count': phrase_count,
            'Contains Money': contains_money
        }
        
        news_data.append(new_data)

    return news_data

def save_data_to_excel(data, file_path):
    """
    Save the extracted data to an Excel file
    """
    excel = Excel()
    excel.create_workbook(file_path)
    excel.append_worksheet(data, "NewsData")
    excel.save_workbook()

def download_image(url, output_dir):
    """
    Download the image from the given URL and save it to the output directory
    """
    if not url:
        return ''
    
    output_dir.mkdir(parents=True, exist_ok=True)
    image_filename = url.split('/')[-1]
    image_path = output_dir / image_filename

    response = requests.get(url)
    response.raise_for_status()

    with open(image_path, 'wb') as f:
        f.write(response.content)

    return image_filename

