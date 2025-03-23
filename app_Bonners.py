import requests
from bs4 import BeautifulSoup
import json
import re
import pandas as pd

def scrape_bonners_price(url, headers=None):
    if not url or pd.isna(url):
        return None
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Method 1: Look for price in the raw HTML using regex based on the pattern you provided
        price_pattern = re.compile(r'"price":{"amount":(\d+(?:\.\d+)?)')
        price_match = price_pattern.search(response.text)
        
        if price_match:
            return price_match.group(1)  # Return the captured price
        
        # Method 2: Try alternative pattern
        alt_price_pattern = re.compile(r'"amount":(\d+(?:\.\d+)?),"currencyCode":"GBP"')
        alt_price_match = alt_price_pattern.search(response.text)
        
        if alt_price_match:
            return alt_price_match.group(1)  # Return the captured price
        
        # Method 3: Try to find scripts that might contain product data
        soup = BeautifulSoup(response.text, "html.parser")
        scripts = soup.find_all("script")
        for script in scripts:
            if script.string and '"price":{"amount":' in script.string:
                price_match = re.search(r'"price":{"amount":(\d+(?:\.\d+)?)', script.string)
                if price_match:
                    return price_match.group(1)
            elif script.string and '"amount":' in script.string and '"currencyCode":"GBP"' in script.string:
                price_match = re.search(r'"amount":(\d+(?:\.\d+)?),"currencyCode":"GBP"', script.string)
                if price_match:
                    return price_match.group(1)
        
        # Method 4: Look for structured data
        jsonld_scripts = soup.find_all("script", type="application/ld+json")
        for script in jsonld_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and "offers" in data:
                    offers = data["offers"]
                    if isinstance(offers, dict) and "price" in offers:
                        return offers["price"]
            except:
                pass
        
        return None
        
    except Exception as e:
        print(f"Error scraping Bonners {url}: {e}")
        return None