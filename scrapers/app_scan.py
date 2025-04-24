import requests
from bs4 import BeautifulSoup
import json
import re
import pandas as pd

def scrape_scan_price(url, headers=None):
    if not url or pd.isna(url):
        return None
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Method 1: Look for price in span with itemprop="price" using regex
        price_pattern = re.compile(r'<span itemprop="price" content="(\d+(?:\.\d+)?)"')
        price_match = price_pattern.search(response.text)
        
        if price_match:
            return price_match.group(1)  # Return the captured price
        
        # Method 2: Try a more generic price pattern
        generic_price_pattern = re.compile(r'"price":\s*"?(\d+(?:\.\d+)?)"?')
        generic_price_match = generic_price_pattern.search(response.text)
        
        if generic_price_match:
            return generic_price_match.group(1)
        
        # Method 3: Try to find scripts that might contain product data
        soup = BeautifulSoup(response.text, "html.parser")
        scripts = soup.find_all("script")
        for script in scripts:
            if script.string:
                # Look for price pattern
                price_match = re.search(r'"price":\s*"?(\d+(?:\.\d+)?)"?', script.string)
                if price_match:
                    return price_match.group(1)
        
        # Method 4: Use BeautifulSoup to find the price span directly
        price_span = soup.find("span", attrs={"itemprop": "price"})
        if price_span and price_span.has_attr("content"):
            return price_span["content"]
        
        # Method 5: Look for structured data
        jsonld_scripts = soup.find_all("script", type="application/ld+json")
        for script in jsonld_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    # Check for offers
                    if "offers" in data:
                        offers = data["offers"]
                        if isinstance(offers, dict) and "price" in offers:
                            return offers["price"]
                    # Direct price
                    if "price" in data:
                        return data["price"]
            except:
                pass
        
        return None
        
    except Exception as e:
        print(f"Error scraping Scan.co.uk {url}: {e}")
        return None