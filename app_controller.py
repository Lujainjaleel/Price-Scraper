import os
import sys
import importlib.util
import pandas as pd
import argparse
import random
import time
from tqdm import tqdm
import re

# Define the file path for the Excel file
EXCEL_FILE_PATH = os.path.join(os.getcwd(), "processed", "processed_Price_Matching.xlsx")

# Define a list of rotating user agents (desktop only)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36 Edg/92.0.902.78",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:90.0) Gecko/20100101 Firefox/90.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:90.0) Gecko/20100101 Firefox/90.0"
]

# Define different accept headers
ACCEPT_HEADERS = [
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
]

# Define different accept language headers (prioritizing UK English)
ACCEPT_LANGUAGE_HEADERS = [
    "en-GB,en;q=0.9",
    "en-GB,en-US;q=0.9,en;q=0.8",
    "en-GB,en;q=0.8",
    "en-US,en-GB;q=0.9,en;q=0.8"
]

# Define the domain to scraper mapping
DOMAIN_SCRAPERS = {
    "andertons.co.uk": {
        "file": "app_Andertons.py",
        "function": "scrape_andertons_price",
        "price_column": "Andertons_Price",
        "url_column": "Competitor URL: andertons.co.uk"
    },
    "bonnersmusic.co.uk": {
        "file": "app_Bonners.py",
        "function": "scrape_bonners_price",
        "price_column": "Bonners_Price",
        "url_column": "Competitor URL: bonnersmusic.co.uk"
    },
    "musicmatter.co.uk": {
        "file": "app_MusicMatters.py",
        "function": "scrape_musicmatter_price",
        "price_column": "MusicMatter_Price",
        "url_column": "Competitor URL: musicmatters.co.uk"
    },
    "guitarguitar.co.uk": {
        "file": "app_GG.py",
        "function": "scrape_guitarguitar_price",
        "price_column": "GuitarGuitar_Price",
        "url_column": "Competitor URL: guitarguitar.co.uk"
    },
    "gak.co.uk": {
        "file": "app_GAK.py",
        "function": "scrape_gak_price",
        "price_column": "GAK_Price",
        "url_column": "Competitor URL: gak.co.uk"
    },
    "pmtonline.co.uk": {
        "file": "app_PMT.py",
        "function": "scrape_pmt_price",
        "price_column": "PMT_Price",
        "url_column": "Competitor URL: pmtonline.co.uk"
    },
    "rimmersmusic.co.uk": {
        "file": "app_Rimmers.py",
        "function": "scrape_rimmers_price",
        "price_column": "Rimmers_Price",
        "url_column": "Competitor URL: rimmersmusic.co.uk"
    },
    "gear4music.com": {
        "file": "app_Gear4Music.py",
        "function": "scrape_gear4music_price",
        "price_column": "Gear4Music_Price",
        "url_column": "Competitor URL: gear4music.com"
    }
}

def extract_domain(url):
    """Extract the domain from a URL."""
    if pd.isna(url) or not url:
        return None
    
    # Use regex to extract domain
    domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
    if domain_match:
        return domain_match.group(1)
    return None

def load_module(file_path, module_name):
    """Dynamically load a Python module from a file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def main():
    parser = argparse.ArgumentParser(description="Scrape prices from various music retailers.")
    parser.add_argument("--all", action="store_true", help="Scrape all retailers")
    parser.add_argument("--retailers", nargs="+", help="Specific retailers to scrape")
    args = parser.parse_args()
    
    # Load the Excel file
    print(f"Loading Excel file from {EXCEL_FILE_PATH}...")
    df = pd.read_excel(EXCEL_FILE_PATH)
    
    # Determine which retailers to scrape
    retailers_to_scrape = []
    if args.all:
        retailers_to_scrape = list(DOMAIN_SCRAPERS.keys())
    elif args.retailers:
        retailers_to_scrape = args.retailers
    else:
        # Default to all retailers if no arguments provided
        retailers_to_scrape = list(DOMAIN_SCRAPERS.keys())
    
    print(f"Will scrape the following retailers: {retailers_to_scrape}")
    
    # Ensure all price columns exist in the dataframe
    for domain_key in retailers_to_scrape:
        if domain_key in DOMAIN_SCRAPERS:
            price_column = DOMAIN_SCRAPERS[domain_key]["price_column"]
            if price_column not in df.columns:
                print(f"Creating price column: {price_column}")
                df[price_column] = None
    
    # Load all required scraper modules
    scraper_modules = {}
    for domain_key in retailers_to_scrape:
        if domain_key in DOMAIN_SCRAPERS:
            scraper_info = DOMAIN_SCRAPERS[domain_key]
            file_path = scraper_info["file"]
            
            # Check if the file exists
            if not os.path.exists(file_path):
                print(f"Warning: Scraper file {file_path} for {domain_key} does not exist. Skipping.")
                continue
                
            module_name = os.path.basename(file_path).replace(".py", "")
            try:
                module = load_module(file_path, module_name)
                scraper_modules[domain_key] = {
                    "module": module,
                    "function": getattr(module, scraper_info["function"]),
                    "price_column": scraper_info["price_column"],
                    "url_column": scraper_info["url_column"]
                }
                print(f"Loaded scraper for {domain_key}")
            except Exception as e:
                print(f"Error loading scraper for {domain_key}: {e}")
    
    # Process each retailer and scrape prices
    total_urls = 0
    for domain_key in retailers_to_scrape:
        if domain_key in scraper_modules:
            scraper_info = scraper_modules[domain_key]
            url_column = scraper_info["url_column"]
            
            # Check if the URL column exists in the dataframe
            if url_column in df.columns:
                # Count non-empty URLs
                valid_urls = df[url_column].dropna().count()
                total_urls += valid_urls
                print(f"Found {valid_urls} URLs for {domain_key}")
            else:
                print(f"Warning: URL column '{url_column}' not found in the Excel file for {domain_key}")
    
    print(f"Found {total_urls} URLs to process for the selected retailers.")
    
    # Use tqdm for a progress bar
    processed_count = 0
    with tqdm(total=total_urls, desc="Scraping") as pbar:
        for domain_key in retailers_to_scrape:
            if domain_key in scraper_modules:
                scraper_info = scraper_modules[domain_key]
                url_column = scraper_info["url_column"]
                price_column = scraper_info["price_column"]
                scraper_function = scraper_info["function"]
                
                # Check if the URL column exists in the dataframe
                if url_column in df.columns:
                    # Process each URL for this retailer
                    for index, row in df.iterrows():
                        url = row.get(url_column)
                        if pd.isna(url) or not url:
                            continue
                            
                        # Generate random headers
                        headers = {
                            "User-Agent": random.choice(USER_AGENTS),
                            "Accept": random.choice(ACCEPT_HEADERS),
                            "Accept-Language": random.choice(ACCEPT_LANGUAGE_HEADERS)
                        }
                        
                        # Call the scraper function
                        try:
                            price = scraper_info["function"](url, headers=headers)
                            
                            # Update the dataframe with the price
                            df.at[index, price_column] = price
                            
                            processed_count += 1
                            pbar.update(1)
                            
                            # Add a small delay to avoid overwhelming the server
                            time.sleep(random.uniform(1, 3))
                            
                            # Save progress every 20 processed URLs
                            if processed_count % 20 == 0:
                                print(f"\nSaving progress after {processed_count} URLs...")
                                df.to_excel(EXCEL_FILE_PATH, index=False)
                                
                        except Exception as e:
                            print(f"\nError scraping {url}: {e}")
                            pbar.update(1)
    
    # Save the final results
    print("\nSaving final results...")
    df.to_excel(EXCEL_FILE_PATH, index=False)
    print(f"Done! Processed {processed_count} URLs.")

if __name__ == "__main__":
    main()