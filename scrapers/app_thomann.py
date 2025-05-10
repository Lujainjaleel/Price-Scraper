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
        
        # First try: Direct regex pattern for the price
        price_pattern = r'<span class="fx-typography-price-primary[^>]*>\s*£\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)'
        price_match = re.search(price_pattern, response.text)
        if price_match:
            return price_match.group(1).replace(',', '')
            
        # Second try: Look for price with price__symbol
        price_pattern2 = r'<span class="price__symbol">£</span>\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)'
        price_match = re.search(price_pattern2, response.text)
        if price_match:
            return price_match.group(1).replace(',', '')
            
        # Third try: Use BeautifulSoup to find any price
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Look for any span containing a price
        for span in soup.find_all("span"):
            text = span.get_text().strip()
            if "£" in text:
                price_match = re.search(r'£\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)', text)
                if price_match:
                    return price_match.group(1).replace(',', '')
        
        # Fourth try: Look in scripts
        scripts = soup.find_all("script")
        for script in scripts:
            if script.string:
                price_match = re.search(r'"price":\s*"?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)"?', script.string)
                if price_match:
                    return price_match.group(1).replace(',', '')
        
        # Fifth try: Look for structured data
        jsonld_scripts = soup.find_all("script", type="application/ld+json")
        for script in jsonld_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    if "offers" in data:
                        offers = data["offers"]
                        if isinstance(offers, dict) and "price" in offers:
                            price = str(offers["price"])
                            return price.replace(',', '')
                    if "price" in data:
                        price = str(data["price"])
                        return price.replace(',', '')
            except:
                pass
        
        return None
        
    except Exception as e:
        print(f"Error scraping Thomann.co.uk {url}: {e}")
        return None