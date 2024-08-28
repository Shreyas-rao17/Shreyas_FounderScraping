# Shreyas_FounderScraping
# Company Founder Scraper

## Overview

This script is designed to extract the names of founders of companies from multiple sources, including the Coresignal API, Gemini AI, Google Search, and Wikipedia. The results are compiled into a CSV file (`founders.csv`). The script operates sequentially, attempting to retrieve founder information from each source until a result is found.

## Features

- **Coresignal API**: Retrieves company founders and website URLs.
- **Gemini AI**: Uses natural language processing to generate potential founder names.
- **Google Search**: Scrapes search results for founder information.
- **Wikipedia**: Searches for the company on Wikipedia and extracts founder details from the page.

## Prerequisites

- **Python 3.x**: Ensure you have Python installed on your machine.
- **Libraries**: Install required Python packages via `pip`:
  ```bash
  pip install requests beautifulsoup4 googlesearch-python google-generativeai
## Setup

### API Keys
Replace the hard-coded values for `CORESIGNAL_API_KEY` and `GEMINI_API_KEY` in the code with your actual API keys.

### Company Names
Prepare a CSV file named `companies.csv` containing a list of company names in the first column. Example:

```csv
CompanyName
Apple Inc.
Google LLC
Microsoft Corporation
```
## Logging

The script logs its activities in `scraping.log`, which can be checked for detailed error messages or processing steps.

## How to Run

1. Ensure your `companies.csv` file is in the same directory as the script.

2. Run the script using the command:

    ```bash
    python script.py
    ```

   The script will start processing each company name and will output the results in a `founders.csv` file.

## Outputs

- **founders.csv**: This file contains two columns: `Company` and `Founder`. If no founder information is found, 'NA' will be recorded in the founder field.

## Error Handling

- **Logging**: Errors and important events are logged in `scraping.log`.
- **Empty Company List**: If the `companies.csv` file is empty or incorrectly formatted, an error will be logged.
- **API Failures**: Each API call is wrapped in try-except blocks to handle request errors. If an API fails, the script moves on to the next available method.
- **Website Scraping**: If no specific founder information is found via Google Search, the script will attempt to find it via Wikipedia.

## Further Improvements

### Enhanced Models and Libraries

1. **Bing Search API**
   - The Bing Search API offers advanced search capabilities and could potentially provide more accurate results compared to Google Search. Integrating it could enhance the quality of the data retrieved from web searches.

2. **OpenAI API**
   - OpenAI's language models, like GPT-4 or newer, could improve the extraction and generation of founder names from text. They are designed to understand and generate human-like text, which may yield more accurate results than the current Gemini model.

3. **Named Entity Recognition (NER) Libraries**
   - Using advanced NER libraries such as SpaCy with pre-trained models or custom-trained models can enhance the extraction of specific entities like founder names from unstructured text. Integrating NER can improve accuracy in extracting relevant information from scraped content.

4. **Knowledge Graphs**
   - Incorporating knowledge graphs, such as those from companies like Wikidata or DBpedia, can provide a structured source of information about companies and their founders. This can complement the existing methods and improve result accuracy.

5. **Data Enrichment APIs**
   - APIs like Clearbit or FullContact offer detailed company and executive information. Leveraging such services could provide richer and more accurate data about founders.

### Potential Enhancements

- **API Rate Limiting and Caching**
  - Implement rate limiting and caching strategies to handle API usage more efficiently and reduce costs associated with API requests.

- **Error Handling and Retry Logic**
  - Improve error handling and implement more robust retry logic for API requests and web scraping to handle transient issues more gracefully.

- **User Interface**
  - Develop a user interface to allow users to input company names and view results interactively, which could make the tool more user-friendly.

By integrating these improvements, the program's accuracy and efficiency in retrieving founder information can be significantly enhanced.

