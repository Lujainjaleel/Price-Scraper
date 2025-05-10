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
        soup = BeautifulSoup(response.text, "html.parser")
        
        # List of possible price locations to check
        price_locations = [
            # Location 1: product__meta-info
            lambda: soup.find("div", class_="product__meta-info"),
            # Location 2: price fx-text
            lambda: soup.find("div", class_="price fx-text"),
            # Location 3: details__price
            lambda: soup.find("div", class_="details__price"),
            # Location 4: price with strike-highlight
            lambda: soup.find("div", class_="fx-price-group--strike-highlight")
        ]
        
        # Try each location
        for get_location in price_locations:
            location = get_location()
            if location:
                # Try to find price in span with fx-typography-price-primary class
                price_span = location.find("span", class_="fx-typography-price-primary")
                if price_span:
                    price_text = price_span.get_text().strip()
                    price_match = re.search(r'£(\d{1,3}(?:,\d{3})*(?:\.\d+)?)', price_text)
                    if price_match:
                        return price_match.group(1).replace(',', '')
                
                # Try to find price in span with price__symbol
                price_symbol = location.find("span", class_="price__symbol")
                if price_symbol:
                    # Get the text after the price symbol
                    price_text = price_symbol.next_sibling.strip()
                    price_match = re.search(r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)', price_text)
                    if price_match:
                        return price_match.group(1).replace(',', '')
        
        # If no price found in HTML structure, try regex patterns
        price_patterns = [
            r'<span class="fx-typography-price-primary[^>]*>\s*£(\d{1,3}(?:,\d{3})*(?:\.\d+)?)',
            r'<span class="price__symbol">£</span>(\d{1,3}(?:,\d{3})*(?:\.\d+)?)',
            r'class="fx-price-group[^"]*">\s*<span[^>]*>\s*£(\d{1,3}(?:,\d{3})*(?:\.\d+)?)'
        ]
        
        for pattern in price_patterns:
            price_match = re.search(pattern, response.text)
            if price_match:
                return price_match.group(1).replace(',', '')
        
        # Try to find in scripts
        scripts = soup.find_all("script")
        for script in scripts:
            if script.string:
                # Look for price pattern with comma support
                price_match = re.search(r'"price":\s*"?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)"?', script.string)
                if price_match:
                    return price_match.group(1).replace(',', '')
        
        # Look for structured data
        jsonld_scripts = soup.find_all("script", type="application/ld+json")
        for script in jsonld_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    # Check for offers
                    if "offers" in data:
                        offers = data["offers"]
                        if isinstance(offers, dict) and "price" in offers:
                            price = str(offers["price"])
                            return price.replace(',', '')
                    # Direct price
                    if "price" in data:
                        price = str(data["price"])
                        return price.replace(',', '')
            except:
                pass
        
        return None
        
    except Exception as e:
        print(f"Error scraping Thomann.co.uk {url}: {e}")
        return None