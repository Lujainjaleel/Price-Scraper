import requests
from bs4 import BeautifulSoup
import json
import re
import pandas as pd
import time
from tqdm import tqdm  # For progress bar

def scrape_amazon_price(url):
    if not url or pd.isna(url):
        return None
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Method 1: Look for the main product price specifically
        # These are the most reliable selectors for the main product price
        main_price_selectors = [
            '#corePrice_feature_div .a-price .a-offscreen',  # Most common location
            '#price_inside_buybox',                          # Buy box price
            '#priceblock_ourprice',                          # Classic price element
            '#priceblock_dealprice',                         # Deal price
            '.a-price[data-a-color="price"] .a-offscreen',   # Another common format
            '#price .a-text-price .a-offscreen'              # List price format
        ]
        
        for selector in main_price_selectors:
            price_element = soup.select_one(selector)
            if price_element:
                price_text = price_element.get_text().strip()
                # Extract numeric value from price text (e.g., "£199.00" -> "199.00")
                price_match = re.search(r'[\d,.]+', price_text)
                if price_match:
                    # Remove commas and currency symbols
                    price = price_match.group(0).replace(',', '')
                    return price
        
        # Method 2: Look for price in the raw HTML using regex based on the pattern you provided
        # This is specifically for the input field pattern you mentioned
        price_pattern = re.compile(r'name="items\[0\.base\]\[customerVisiblePrice\]\[amount\]" value="(\d+(?:\.\d+)?)"')
        price_match = price_pattern.search(response.text)
        
        if price_match:
            return price_match.group(1)  # Return the captured price
        
        # Method 3: Try to find input elements with the specific name attribute
        price_input = soup.select('input[name="items[0.base][customerVisiblePrice][amount]"]')
        
        if price_input and price_input[0].has_attr('value'):
            return price_input[0]['value']
        
        # Method 4: Look for structured data (more reliable for the main product)
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
        
        # Method 5: Look for price in the twister data (Amazon's product variation data)
        twister_pattern = re.compile(r'"twister-plus-price-data"[^>]*>([^<]+)')
        twister_match = twister_pattern.search(response.text)
        if twister_match:
            try:
                twister_data = json.loads(twister_match.group(1))
                if "price" in twister_data:
                    price_text = twister_data["price"]
                    price_match = re.search(r'[\d,.]+', price_text)
                    if price_match:
                        return price_match.group(0).replace(',', '')
            except:
                pass
        
        return None
        
    except Exception as e:
        print(f"Error scraping Amazon {url}: {e}")
        return None

def main():
    # File path
    file_path = "/Users/lujainjaleel/PriceAnalysisTool/Price Matching1.xlsx"
    
    # Read the Excel file
    print("Reading Excel file...")
    df = pd.read_excel(file_path)
    
    # Check if the Amazon column exists
    if "Amazon" not in df.columns:
        print("Error: 'Amazon' column not found in the Excel file.")
        return
        
    # Create a new column for prices if it doesn't exist
    if "Amazon_Price" not in df.columns:
        df["Amazon_Price"] = None
    
    # Count non-empty URLs
    valid_urls = df["Amazon"].dropna().count()
    print(f"Found {valid_urls} Amazon URLs to process.")
    
    # Process each URL and scrape the price
    print("Scraping Amazon prices...")
    
    # Use tqdm for a progress bar
    for index, row in tqdm(df.iterrows(), total=len(df), desc="Scraping"):
        url = row["Amazon"]
        
        # Skip empty URLs
        if pd.isna(url) or not url:
            continue
        
        # Scrape the price
        price = scrape_amazon_price(url)
        
        # Update the dataframe
        df.at[index, "Amazon_Price"] = price
        
        # Add a small delay to avoid overwhelming the server
        time.sleep(2)  # Longer delay for Amazon to avoid being blocked
        
        # Save progress every 50 rows
        if index % 50 == 0 and index > 0:
            print(f"Saving progress after {index} rows...")
            df.to_excel(file_path, index=False)
    
    # Save the final results
    print("Saving final results...")
    df.to_excel(file_path, index=False)
    print("Done! Prices have been scraped and saved to the 'Amazon_Price' column.")

if __name__ == "__main__":
    main()
