import requests
from bs4 import BeautifulSoup
import json
import re
import pandas as pd

def scrape_pmt_price(url, headers=None):
    if not url or pd.isna(url):
        return None
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Method 1: Look for price in the raw HTML using regex based on the pattern you provided
        price_pattern = re.compile(r'"price":(\d+(?:\.\d+)?)')
        price_match = price_pattern.search(response.text)
        
        if price_match:
            return price_match.group(1)  # Return the captured price
        
        # Method 2: Try to find data attributes that might contain price info
        soup = BeautifulSoup(response.text, "html.parser")
        elements_with_attributes = soup.select('[data-attributes]')
        
        for element in elements_with_attributes:
            attributes = element.get('data-attributes', '')
            if '"price":' in attributes:
                price_match = re.search(r'"price":(\d+(?:\.\d+)?)', attributes)
                if price_match:
                    return price_match.group(1)
        
        # Method 3: Try to find scripts that might contain product data
        scripts = soup.find_all("script")
        for script in scripts:
            if script.string and '"price":' in script.string:
                price_match = re.search(r'"price":(\d+(?:\.\d+)?)', script.string)
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
        print(f"Error scraping PMT {url}: {e}")
        return None