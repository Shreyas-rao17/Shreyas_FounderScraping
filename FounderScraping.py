import csv
import requests
import logging
from bs4 import BeautifulSoup
from googlesearch import search
import json
import asyncio
import urllib.parse
import google.generativeai as genai
import re
import os

# Configure logging to write messages to 'scraping.log' with INFO level
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename='scraping.log', filemode='w')

# Load API keys from environment variables (replace hardcoded values if needed)
CORESIGNAL_API_KEY = 'eyJhbGciOiJFZERTQSIsImtpZCI6IjQ3ZmFjZDgzLWQ1NmUtMjk3MC04YmNhLTkzNTY5OTc3MmU0MCJ9.eyJhdWQiOiIxODBkYy5vcmciLCJleHAiOjE3NTYxNTc1MTIsImlhdCI6MTcyNDYwMDU2MCwiaXNzIjoiaHR0cHM6Ly9vcHMuY29yZXNpZ25hbC5jb206ODMwMC92MS9pZGVudGl0eS9vaWRjIiwibmFtZXNwYWNlIjoicm9vdCIsInByZWZlcnJlZF91c2VybmFtZSI6IjE4MGRjLm9yZyIsInN1YiI6ImZhMGM0YzljLWMyMWMtZmZkZi1jMGI5LTQ4YWVkNWFmOWMxNiIsInVzZXJpbmZvIjp7InNjb3BlcyI6ImNkYXBpIn19.GoSZURZ8FcT9068yMbmPKnYxcN_ucQ01t26R8sNMgysbZj-tpNoUZRJdLJmVu0EoBlJ4SHYvSQtFeS5CJartBg'  # Replace with your Coresignal API key
GEMINI_API_KEY = 'AIzaSyDDFHjerywhIiPSLpaSpM1559nlS2hm_UE'  # Replace with your Gemini API key
CORESIGNAL_API_URL = "https://api.coresignal.com/cdapi/v1/linkedin/member/search/filter"

def get_session():
    """
    Create and configure a requests.Session object with retry strategy.
    """
    session = requests.Session()
    retry = requests.adapters.Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
    adapter = requests.adapters.HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def read_company_names(file_path):
    """
    Read company names from a CSV file and return them as a list of strings.
    
    Parameters:
        file_path (str): Path to the CSV file containing company names.
    
    Returns:
        list: A list of company names.
    """
    try:
        logging.debug(f"Attempting to read company names from file: {file_path}")
        with open(file_path, mode='r') as file:
            reader = csv.reader(file)
            company_names = [row[0].strip() for row in reader if row]
        logging.debug(f"Company names read: {company_names}")
        if not company_names:
            logging.error("No company names were found in the file. The file might be empty or not formatted correctly.")
        return company_names
    except FileNotFoundError:
        logging.error(f"File {file_path} not found.")
        return []
    except Exception as e:
        logging.error(f"Error reading company names from {file_path}: {e}")
        return []

def write_results_to_csv(results, file_path):
    """
    Write results to a CSV file.

    Parameters:
        results (list): A list of tuples containing company names and founder names.
        file_path (str): Path to the output CSV file.
    """
    try:
        with open(file_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Company', 'Founder'])  # Write header row
            writer.writerows(results)  # Write data rows
    except Exception as e:
        logging.error(f"Error writing results to {file_path}: {e}")

def get_founder_and_website_from_coresignal(company_name):
    """
    Fetch founder information from Coresignal API.

    Parameters:
        company_name (str): Name of the company.

    Returns:
        tuple: A tuple containing a list of founder names and website URL (both may be None).
    """
    if not CORESIGNAL_API_KEY:
        logging.error("Coresignal API key is missing.")
        return None, None
    session = get_session()
    try:
        payload = json.dumps({
            "experience_title": "Co-founder",
            "experience_deleted": "False",
            "active_experience": "False",
            "experience_company_name": company_name
        })
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {CORESIGNAL_API_KEY}'
        }
        response = session.post(CORESIGNAL_API_URL, headers=headers, data=payload)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()
        if 'data' in data and len(data['data']) > 0:
            company_data = data['data'][0]
            founders = company_data.get('founders', [])
            founder_names = [f"{founder['first_name']} {founder['last_name']}" for founder in founders]
            return founder_names if founder_names else None, None
    except requests.RequestException as e:
        logging.error(f"Error fetching data from Coresignal for {company_name}: {e}")
    return None, None

def get_founder_from_gemini(company_name):
    """
    Fetch founder information from Gemini API.

    Parameters:
        company_name (str): Name of the company.

    Returns:
        list: A list of founder names extracted from the Gemini API response.
    """
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Who is the founder of the company {company_name}?"
        response = model.generate_content(prompt)
        response_text = response.text

        # Regular expression to find founder names in the response text
        founder_pattern = re.compile(r"(?:founder|founded|co-founder|started)\s*[:\-]?\s*([A-Z][a-zA-Z]+\s[A-Z][a-zA-Z]+)")
        founders = founder_pattern.findall(response_text)

        if founders:
            return founders
        else:
            logging.error(f"Gemini API did not return a recognizable founder name for {company_name}")
            return None

    except Exception as e:
        logging.error(f"Error fetching data from Gemini for {company_name}: {e}")
        return None

def scrape_google_for_founder(company_name):
    """
    Scrape Google search results for founder information.

    Parameters:
        company_name (str): Name of the company.

    Returns:
        str: The founder's name or 'NA' if not found.
    """
    try:
        query = f"{company_name} founder"
        search_results = search(query, num_results=1)
        for url in search_results:
            logging.info(f"Google search URL: {url}")
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')

            text = soup.get_text()
            # Regular expression to find founder names in the text
            founder_pattern = re.compile(
                r"(?:founder|co-founder|established by|created by|started by)\s*(?:by)?\s*([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+){1,2})"
            )
            match = founder_pattern.search(text)

            if match:
                name = match.group(1)
                logging.info(f"Found name via regex: {name}")
                return name.replace(",", "")
            else:
                logging.info(f"No specific founder name found on Google for {company_name}. Moving to Wikipedia scraping.")
                return "NA"

        return "NA"

    except Exception as e:
        logging.error(f"Error scraping Google for {company_name}: {e}")
        return "NA"

def search_wikipedia(company_name):
    """
    Search Wikipedia for founder information.

    Parameters:
        company_name (str): Name of the company.

    Returns:
        str: The founder's name or a message indicating the result of the search.
    """
    search_url = "https://en.wikipedia.org/w/api.php"
    params = {
        'action': 'query',
        'format': 'json',
        'list': 'search',
        'srsearch': company_name,
        'utf8': 1
    }

    response = requests.get(search_url, params=params)

    if response.status_code != 200:
        logging.error(f"Failed to retrieve search results for {company_name}")
        return "Failed to retrieve search results"

    search_results = response.json()
    search_hits = search_results.get('query', {}).get('search', [])

    if not search_hits:
        logging.error(f"No search results found for {company_name}")
        return "No search results found"

    page_title = search_hits[0]['title']
    page_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(page_title)}"

    response = requests.get(page_url)

    if response.status_code != 200:
        logging.error(f"Failed to retrieve the page: {page_url}")
        return f"Failed to retrieve the page: {page_url}"

    soup = BeautifulSoup(response.text, 'html.parser')

    infobox = soup.find('table', {'class': 'infobox'})
    if infobox:
        rows = infobox.find_all('tr')
        founders = []
        for row in rows:
            header = row.find('th')
            if header and 'Founder' in header.get_text():
                founder = row.find('td')
                if founder:
                    founders.append(founder.get_text(strip=True))
        if founders:
            return ', '.join(founders)
    return "Founder information not found"

async def main():
    """
    Main function to orchestrate the processing of company names and fetching founder information.
    """
    company_names = read_company_names('companies.csv')
    results = []

    for company in company_names:
        # Try to get founder information from Coresignal
        founders, _ = get_founder_and_website_from_coresignal(company)
        if founders:
            results.append((company, ', '.join(founders)))
        else:
            # Try to get founder information from Gemini
            founders = get_founder_from_gemini(company)
            if founders:
                results.append((company, ', '.join(founders)))
            else:
                # Try to scrape Google for founder information
                founder = scrape_google_for_founder(company)
                if founder and founder != "NA":
                    results.append((company, founder))
                else:
                    # Try to get founder information from Wikipedia
                    founder = search_wikipedia(company)
                    if founder and founder != "Founder information not found":
                        results.append((company, founder))
                    else:
                        results.append((company, 'NA'))

    logging.info(f"Results to be written to CSV: {results}")
    write_results_to_csv(results, 'founders.csv')

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        print(f"An unexpected error occurred: {e}")
