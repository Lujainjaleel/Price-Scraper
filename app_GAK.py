import requests
from bs4 import BeautifulSoup
import json
import re
import pandas as pd

def scrape_gak_price(url, headers=None):
    if not url or pd.isna(url):
        return None
    
    try:
        print(f"Scraping GAK URL: {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Debug: Check if we got a response
        print(f"Response status: {response.status_code}")
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Method 1: Look for data-price attribute in product cards
        product_cards = soup.select('.product-card, [data-price]')
        for card in product_cards:
            price = card.get('data-price')
            if price:
                print(f"Found price with Method 1: {price}")
                return price
        
        # Method 2: Look for price in the raw HTML using regex
        price_pattern = re.compile(r'data-price="(\d+(?:\.\d+)?)"')
        price_match = price_pattern.search(response.text)
        
        if price_match:
            price = price_match.group(1)
            print(f"Found price with Method 2: {price}")
            return price
        
        # Method 3: Try alternative pattern
        alt_price_pattern = re.compile(r'"price":(\d+(?:\.\d+)?)')
        alt_price_match = alt_price_pattern.search(response.text)
        
        if alt_price_match:
            price = alt_price_match.group(1)
            print(f"Found price with Method 3: {price}")
            return price
        
        # Method 4: Try to find scripts that might contain product data
        scripts = soup.find_all("script")
        for script in scripts:
            if script.string and '"price":' in script.string:
                price_match = re.search(r'"price":(\d+(?:\.\d+)?)', script.string)
                if price_match:
                    price = price_match.group(1)
                    print(f"Found price with Method 4 (script): {price}")
                    return price
        
        # Method 5: Look for structured data
        jsonld_scripts = soup.find_all("script", type="application/ld+json")
        for script in jsonld_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and "offers" in data:
                    offers = data["offers"]
                    if isinstance(offers, dict) and "price" in offers:
                        price = offers["price"]
                        print(f"Found price with Method 5 (script): {price}")
                        return price
            except Exception as e:
                print(f"Error parsing JSON-LD script: {e}")
        
        # Method 6: Try to find price elements directly
        price_element = soup.select_one('.price')
        if price_element:
            price_text = price_element.get_text().strip()
            prices = re.findall(r'£(\d+\.\d+)', price_text)
            if prices:
                max_price = max([float(p) for p in prices])
                print(f"Found price with Method 6: {max_price}")
                return max_price
        
        # Debug: If we couldn't find a price, save a sample of the HTML
        with open("gak_debug.html", "w") as f:
            f.write(response.text[:10000])  # Save first 10000 chars to avoid huge files
        print(f"No price found. Saved sample HTML to gak_debug.html")
        
        return None
        
    except Exception as e:
        print(f"Error scraping GAK {url}: {e}")
        return None