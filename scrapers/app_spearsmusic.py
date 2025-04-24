import requests
from bs4 import BeautifulSoup
import json
import re
import pandas as pd

def scrape_spearsmusic_price(url, headers=None):
    if not url or pd.isna(url):
        return None
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Method 1: Look for price in Offers JSON structure
        offers_pattern = re.compile(r'"Offers":\s*{\s*"@type":\s*"Offer",\s*"priceCurrency":\s*"GBP",\s*"price":\s*"(\d+(?:\.\d+)?)"')
        offers_match = offers_pattern.search(response.text)
        
        if offers_match:
            return offers_match.group(1)  # Return the captured price
        
        # Method 2: Try a more generic price pattern
        price_pattern = re.compile(r'"price":\s*"(\d+(?:\.\d+)?)"')
        price_match = price_pattern.search(response.text)
        
        if price_match:
            return price_match.group(1)
        
        # Method 3: Try to find scripts that might contain product data
        soup = BeautifulSoup(response.text, "html.parser")
        scripts = soup.find_all("script")
        for script in scripts:
            if script.string:
                # Look for price in Offers structure
                offers_match = re.search(r'"Offers":\s*{\s*"@type":\s*"Offer",\s*"priceCurrency":\s*"GBP",\s*"price":\s*"(\d+(?:\.\d+)?)"', script.string)
                if offers_match:
                    return offers_match.group(1)
                
                # Look for generic price
                price_match = re.search(r'"price":\s*"(\d+(?:\.\d+)?)"', script.string)
                if price_match:
                    return price_match.group(1)
        
        # Method 4: Look for structured data
        jsonld_scripts = soup.find_all("script", type="application/ld+json")
        for script in jsonld_scripts:
            try:
                data = json.loads(script.string)
                # Check for different possible structures
                if isinstance(data, dict):
                    # Direct offers
                    if "offers" in data:
                        offers = data["offers"]
                        if isinstance(offers, dict) and "price" in offers:
                            return offers["price"]
                    # Nested offers
                    if "Offers" in data:
                        offers = data["Offers"]
                        if isinstance(offers, dict) and "price" in offers:
                            return offers["price"]
                    # Direct price
                    if "price" in data:
                        return data["price"]
            except:
                pass
        
        return None
        
    except Exception as e:
        print(f"Error scraping Spears Music {url}: {e}")
        return None