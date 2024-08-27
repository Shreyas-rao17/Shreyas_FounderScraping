import csv
import requests
import logging
from bs4 import BeautifulSoup
from googlesearch import search
import json
import asyncio
import urllib.parse
import google.generativeai as genai

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename='scraping.log', filemode='w')

# Replace environment variables with hard-coded values
CORESIGNAL_API_KEY = 'eyJhbGciOiJFZERTQSIsImtpZCI6IjQ3ZmFjZDgzLWQ1NmUtMjk3MC04YmNhLTkzNTY5OTc3MmU0MCJ9.eyJhdWQiOiIxODBkYy5vcmciLCJleHAiOjE3NTYxNTc1MTIsImlhdCI6MTcyNDYwMDU2MCwiaXNzIjoiaHR0cHM6Ly9vcHMuY29yZXNpZ25hbC5jb206ODMwMC92MS9pZGVudGl0eS9vaWRjIiwibmFtZXNwYWNlIjoicm9vdCIsInByZWZlcnJlZF91c2VybmFtZSI6IjE4MGRjLm9yZyIsInN1YiI6ImZhMGM0YzljLWMyMWMtZmZkZi1jMGI5LTQ4YWVkNWFmOWMxNiIsInVzZXJpbmZvIjp7InNjb3BlcyI6ImNkYXBpIn19.GoSZURZ8FcT9068yMbmPKnYxcN_ucQ01t26R8sNMgysbZj-tpNoUZRJdLJmVu0EoBlJ4SHYvSQtFeS5CJartBg'  # Replace with your Coresignal API key
GEMINI_API_KEY = 'AIzaSyDDFHjerywhIiPSLpaSpM1559nlS2hm_UE'  # Replace with your Gemini API key
CORESIGNAL_API_URL = "https://api.coresignal.com/cdapi/v1/linkedin/member/search/filter"

def get_session():
    session = requests.Session()
    retry = requests.adapters.Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = requests.adapters.HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def read_company_names(file_path):
    try:
        logging.debug(f"Attempting to read company names from file: {file_path}")
        with open(file_path, mode='r') as file:
            reader = csv.reader(file)
            company_names = [row[0] for row in reader if row]
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
    try:
        with open(file_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Company', 'Founder'])
            writer.writerows(results)
    except Exception as e:
        logging.error(f"Error writing results to {file_path}: {e}")

def get_founder_and_website_from_coresignal(company_name):
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
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and len(data['data']) > 0:
                company_data = data['data'][0]
                founders = company_data.get('founders', [])
                founder_names = [f"{founder['first_name']} {founder['last_name']}" for founder in founders]
                website_url = company_data.get('website', None)
                return founder_names if founder_names else None, website_url
    except requests.RequestException as e:
        logging.error(f"Error fetching data from Coresignal for {company_name}: {e}")
    return None, None

def get_founder_from_gemini(company_name):
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Who is the founder of the company {company_name}?"
        response = model.generate_content(prompt)
        response_text = response.text

        # Improved extraction logic using regular expressions to find names
        import re

        # Attempt to find common patterns like "Founder: [Name]", "[Name] founded [Company]", etc.
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

import re

import re

import re

def scrape_google_for_founder(company_name):
    try:
        query = f"{company_name} founder"
        search_results = search(query, num_results=1)
        for url in search_results:
            logging.info(f"Google search URL: {url}")
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')

            # Search for specific tag patterns as a first approach
            possible_patterns = [
                ('div', {'class': 'founder-name'}),
                ('span', {'class': 'founder-name'}),
                ('p', {'class': 'founder-name'}),
                ('h1', {'class': 'founder-name'}),
                ('h2', {'class': 'founder-name'}),
                ('div', {'class': 'bio-name'}),
                ('div', {'class': 'bio-info'}),
                ('p', None),
            ]

            for tag, attrs in possible_patterns:
                if attrs:
                    founders = soup.find_all(tag, attrs)
                else:
                    founders = soup.find_all(tag)

                for founder in founders:
                    name = founder.get_text(strip=True)
                    if 2 <= len(name.split()) <= 3:  # Heuristic for likely name patterns
                        return name

            # If specific patterns are not found, search for name patterns in the text
            text = soup.get_text()

            # Regular expression to capture names after keywords like "founder" or "co-founder"
            founder_pattern = re.compile(r"(?:founder|co-founder|established by)\s*(?:by)?\s*([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)?)")
            match = founder_pattern.search(text)

            if match:
                name = match.group(1)
                return name.replace(",", "")
            if not founder or founder in ["No search results found", "Founder information not found"]:
                logging.info(f"No specific founder name found on Google for {company_name}. Moving to Wikipedia scraping.")
                return ""
        return founder

    except Exception as e:
        logging.error(f"Error scraping Google for {company_name}: {e}")
        return "NA"


def search_wikipedia(company_name):
    """
    Searches Wikipedia for the given company name and returns the founder's name if available.

    Parameters:
    company_name (str): The name of the company to search for.

    Returns:
    str: The name of the founder(s) or an error message if the information cannot be retrieved.
    """
    # Define the Wikipedia API endpoint for searching
    search_url = "https://en.wikipedia.org/w/api.php"
    params = {
        'action': 'query',
        'format': 'json',
        'list': 'search',
        'srsearch': company_name,  # The search term (company name)
        'utf8': 1
    }

    # Send a GET request to the Wikipedia API
    response = requests.get(search_url, params=params)

    # Check if the API request was successful
    if response.status_code != 200:
        return "Failed to retrieve search results"

    # Parse the JSON response from the Wikipedia API
    search_results = response.json()
    search_hits = search_results.get('query', {}).get('search', [])

    # If there are no search results, return a message indicating this
    if not search_hits:
        return "No search results found"

    # Retrieve the title of the first search result (most relevant result)
    page_title = search_hits[0]['title']
    page_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(page_title)}"

    # Send a GET request to the Wikipedia page of the company
    response = requests.get(page_url)

    # Check if the page request was successful
    if response.status_code != 200:
        return f"Failed to retrieve the page: {page_url}"

    # Parse the HTML content of the page using BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the infobox on the page (typically contains company details)
    infobox = soup.find('table', {'class': 'infobox'})
    if infobox:
        rows = infobox.find_all('tr')
        founders = []
        for row in rows:
            header = row.find('th')
            # Look for a row that contains 'Founder' in the header
            if header and 'Founder' in header.get_text():
                founder = row.find('td')
                if founder:
                    founders.append(founder.get_text(strip=True))
        # If founders were found, return them as a comma-separated string
        if founders:
            return ', '.join(founders)
    return "Founder information not found"

async def main():
    company_names = read_company_names('companies.csv')
    results = []

    for company in company_names:
        founders, website = get_founder_and_website_from_coresignal(company)
        if founders:
            results.append((company, ', '.join(founders)))
        else:
            founders = get_founder_from_gemini(company)
            if founders:
                results.append((company, ', '.join(founders)))
            else:
                founders = scrape_google_for_founder(company)
                if founders:
                    results.append((company, ', '.join(founders)))
                else:
                    founders = search_wikipedia(company)
                    if founders:
                        results.append((company, ', '.join(founders)))
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
