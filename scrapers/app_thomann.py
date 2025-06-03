import requests
from bs4 import BeautifulSoup
import json
import re
import pandas as pd
from urllib.parse import urlparse

def scrape_thomann_price(url, headers=None):
    if not url or pd.isna(url):
        return None
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Add debug prints for response status and content
        print(f"[Thomann Scraper Debug] HTTP Status Code: {response.status_code}")
        print(f"[Thomann Scraper Debug] First 500 chars of response text: {response.text[:500]}")

        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Normalize the input URL for robust comparison
        parsed_input_url = urlparse(url)
        normalized_input_url = parsed_input_url.scheme + "://" + parsed_input_url.netloc + parsed_input_url.path
        normalized_input_url = normalized_input_url.rstrip('/')

        # --- ONLY try: Find price specifically within the main product price box with URL validation ---
        product_price_block = soup.find("div", class_="product-price-box")
        
        if not product_price_block:
            print("[Thomann Scraper] product-price-box div (class) not found.")

        if product_price_block:
            # Try to get price from meta itemprop="price" first
            meta_price_tag = product_price_block.find("meta", itemprop="price")
            # Try to get URL from meta itemprop="url"
            meta_url_tag = product_price_block.find("meta", itemprop="url")

            if meta_price_tag and "content" in meta_price_tag.attrs and \
               meta_url_tag and "content" in meta_url_tag.attrs:
                
                price = meta_price_tag["content"]
                scraped_url = meta_url_tag["content"]
                
                # Normalize the scraped URL for robust comparison
                parsed_scraped_url = urlparse(scraped_url)
                normalized_scraped_url = parsed_scraped_url.scheme + "://" + parsed_scraped_url.netloc + parsed_scraped_url.path
                normalized_scraped_url = normalized_scraped_url.rstrip('/')

                # Validate if the scraped URL matches the input URL after normalization
                if normalized_scraped_url == normalized_input_url:
                    print(f"[Thomann Scraper] Scraped URL {scraped_url} (normalized: {normalized_scraped_url}) matches input URL {url} (normalized: {normalized_input_url}). Returning price from meta tag.")
                    return str(price).replace(',', '')
                else:
                    print(f"[Thomann Scraper] URL mismatch in product-price-box meta tags. Scraped: {scraped_url} (normalized: {normalized_scraped_url}), Expected: {url} (normalized: {normalized_input_url}). Price skipped.")
            else:
                print("[Thomann Scraper] meta itemprop=\"price\" or meta itemprop=\"url\" not found or missing content attribute within product-price-box.")
        
        print("[Thomann Scraper] No valid price found in product-price-box with URL validation. Returning None.")
        return None
        
    except Exception as e:
        print(f"[Thomann Scraper] Error scraping Thomann.co.uk {url}: {e}")
        return None