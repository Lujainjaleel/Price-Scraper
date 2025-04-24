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
        
        # Method 1: Look for price in wishlistheart div's data-price attribute using regex
        wishlist_pattern = re.compile(r'<div class="wishlistheart"[^>]*data-price="(\d+(?:\.\d+)?)"')
        wishlist_match = wishlist_pattern.search(response.text)
        
        if wishlist_match:
            return wishlist_match.group(1)  # Return the captured price
        
        # Method 2: Try a more generic pattern for data-price attribute
        data_price_pattern = re.compile(r'data-price="(\d+(?:\.\d+)?)"')
        data_price_match = data_price_pattern.search(response.text)
        
        if data_price_match:
            return data_price_match.group(1)
        
        # Method 3: Use BeautifulSoup to find the wishlistheart div directly
        soup = BeautifulSoup(response.text, "html.parser")
        wishlist_div = soup.find("div", class_="wishlistheart")
        
        if wishlist_div and wishlist_div.has_attr("data-price"):
            return wishlist_div["data-price"]
        
        # Method 4: Try to find any element with data-price attribute
        element_with_price = soup.find(attrs={"data-price": True})
        if element_with_price:
            return element_with_price["data-price"]
        
        # Method 5: Try to find scripts that might contain product data
        scripts = soup.find_all("script")
        for script in scripts:
            if script.string:
                # Look for price pattern
                price_match = re.search(r'"price":\s*"?(\d+(?:\.\d+)?)"?', script.string)
                if price_match:
                    return price_match.group(1)
        
        # Method 6: Look for structured data
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