import requests
from bs4 import BeautifulSoup
import json
import re
import pandas as pd

def scrape_thomann_price(url, headers=None):
    if not url or pd.isna(url):
        return None
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")
        
        # First try: Look in scripts for JSON-LD, prioritizing product and offer schemas
        jsonld_scripts = soup.find_all("script", type="application/ld+json")
        for script in jsonld_scripts:
            try:
                data = json.loads(script.string)
                # Handle single JSON object or a list of JSON objects
                if not isinstance(data, list):
                    data = [data]

                for item in data:
                    # Prioritize Product schema
                    if item.get("@type") == "Product":
                        if "offers" in item:
                            offers = item["offers"]
                            if isinstance(offers, dict) and "price" in offers:
                                price = str(offers["price"])
                                return price.replace(',', '')
                        elif "price" in item: # Sometimes price is directly in Product schema
                            price = str(item["price"])
                            return price.replace(',', '')
                    # Fallback to Offer schema if Product not found or doesn't have price
                    if item.get("@type") == "Offer" and "price" in item:
                        price = str(item["price"])
                        return price.replace(',', '')
            except json.JSONDecodeError:
                continue # Skip invalid JSON
            except Exception as e:
                print(f"Error parsing JSON-LD: {e}")
                continue
        
        # --- Second try: Find price specifically within the main product price block ---
        product_price_block = soup.find("div", id="product-price-box")
        if product_price_block:
            # Try to get price from meta itemprop="price" first
            meta_price_tag = product_price_block.find("meta", itemprop="price")
            # Try to get URL from meta itemprop="url"
            meta_url_tag = product_price_block.find("meta", itemprop="url")

            if meta_price_tag and "content" in meta_price_tag.attrs and \
               meta_url_tag and "content" in meta_url_tag.attrs:
                
                price = meta_price_tag["content"]
                scraped_url = meta_url_tag["content"]

                # Validate if the scraped URL matches the input URL
                if scraped_url == url:
                    print(f"Scraped URL {scraped_url} matches input URL {url}. Returning price.")
                    return str(price).replace(',', '')
                else:
                    print(f"URL mismatch in product-price-box meta tags. Scraped: {scraped_url}, Expected: {url}. Skipping this price source.")

            # If meta tags didn't provide a valid, matching price, try span with fx-typography-price-primary or price__primary
            price_span = product_price_block.find("span", class_=["fx-typography-price-primary", "price__primary"])
            if price_span:
                text = price_span.get_text().strip()
                price_match = re.search(r'£\s*(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)', text)
                if price_match:
                    return price_match.group(1).replace(',', '')

            # If span not found, try div with class="price"
            price_div = product_price_block.find("div", class_="price")
            if price_div:
                text = price_div.get_text().strip()
                price_match = re.search(r'£\s*(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)', text)
                if price_match:
                    return price_match.group(1).replace(',', '')

        # --- Attempt to remove accessories section elements before further general HTML parsing ---
        # This is to prevent scraping prices from the "Accessories & matching items" section
        accessories_headline = soup.find("h2", class_="fx-carousel__headline", 
                                          text=re.compile(r"Accessories & matching items", re.IGNORECASE))
        
        if accessories_headline:
            # Decompose the headline itself
            accessories_headline.decompose()
            print("Decomposed 'Accessories & matching items' headline.")
            
            # Decompose the immediate sibling div with class 'control' which contains the carousel items
            control_div = accessories_headline.find_next_sibling("div", class_="control")
            if control_div:
                control_div.decompose()
                print("Decomposed 'control' div sibling of accessories headline.")


        # --- Third try: Fallback regex on *original* page text (least specific, use with caution) ---
        price_pattern = r'£\s*(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)'
        price_match = re.search(price_pattern, response.text) # Use original response.text
        if price_match:
            return price_match.group(1).replace(',', '')
        
        return None
        
    except Exception as e:
        print(f"Error scraping Thomann.co.uk {url}: {e}")
        return None