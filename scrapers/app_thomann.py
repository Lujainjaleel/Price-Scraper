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
        
        # First try: Find price in span with fx-typography-price-primary or price__primary
        price_spans = soup.find_all("span", class_=["fx-typography-price-primary", "price__primary"])
        for span in price_spans:
            text = span.get_text().strip()  # Clean whitespace and line breaks
            price_match = re.search(r'£\s*(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)', text)
            if price_match:
                return price_match.group(1).replace(',', '')
        
        # Second try: Handle separated price__symbol (e.g., <span class="price__symbol">£</span>1,444)
        price_divs = soup.find_all("div", class_="price")
        for div in price_divs:
            text = div.get_text().strip()  # Get combined text of div
            price_match = re.search(r'£\s*(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)', text)
            if price_match:
                return price_match.group(1).replace(',', '')
        
        # Third try: Fallback regex on entire page
        price_pattern = r'£\s*(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)'
        price_match = re.search(price_pattern, response.text)
        if price_match:
            return price_match.group(1).replace(',', '')
        
        # Fourth try: Look in scripts for JSON-LD
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