import requests
from bs4 import BeautifulSoup
import json
import re
import pandas as pd

def scrape_gear4music_price(url, headers=None):
    if not url or pd.isna(url):
        return None
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Method 1: Look for unit_price and unit_sale_price in the raw HTML
        price_pattern = re.compile(r'"unit_price":"(\d+(?:\.\d+)?)"')
        price_match = price_pattern.search(response.text)
        
        if price_match:
            return price_match.group(1)  # Return the captured price
        
        # Method 2: Try sale price pattern
        sale_price_pattern = re.compile(r'"unit_sale_price":"(\d+(?:\.\d+)?)"')
        sale_price_match = sale_price_pattern.search(response.text)
        
        if sale_price_match:
            return sale_price_match.group(1)  # Return the captured price
        
        # Method 3: Try standard price pattern
        std_price_pattern = re.compile(r'"price":(\d+(?:\.\d+)?)')
        std_price_match = std_price_pattern.search(response.text)
        
        if std_price_match:
            return std_price_match.group(1)  # Return the captured price
        
        # Method 4: Try alternative pattern
        alt_price_pattern = re.compile(r'"price":\s*"(\d+(?:\.\d+)?)"')
        alt_price_match = alt_price_pattern.search(response.text)
        
        if alt_price_match:
            return alt_price_match.group(1)  # Return the captured price
        
        # Method 5: Try to find scripts that might contain product data
        soup = BeautifulSoup(response.text, "html.parser")
        scripts = soup.find_all("script")
        for script in scripts:
            if script.string:
                # Look for unit_price
                unit_price_match = re.search(r'"unit_price":"(\d+(?:\.\d+)?)"', script.string)
                if unit_price_match:
                    return unit_price_match.group(1)
                
                # Look for unit_sale_price
                sale_price_match = re.search(r'"unit_sale_price":"(\d+(?:\.\d+)?)"', script.string)
                if sale_price_match:
                    return sale_price_match.group(1)
                
                # Look for standard price
                if '"price":' in script.string:
                    price_match = re.search(r'"price":(\d+(?:\.\d+)?)', script.string)
                    if price_match:
                        return price_match.group(1)
        
        # Method 6: Look for structured data
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
        print(f"Error scraping Gear4Music {url}: {e}")
        return None