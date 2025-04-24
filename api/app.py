from flask import Flask, request, jsonify, render_template, redirect, url_for, send_from_directory, send_file
import importlib.util
import os
import re
import random
import time
import json
import uuid
import pandas as pd
import subprocess
from datetime import datetime, timezone, timedelta
from werkzeug.utils import secure_filename
import threading
import shutil
import csv
from io import StringIO
from io import BytesIO
from urllib.parse import urlparse
import dropbox
from dropbox.exceptions import AuthError, ApiError
from dropbox.files import WriteMode
import requests

# Get the absolute path to the project directory
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__, 
            template_folder=os.path.join(PROJECT_DIR, 'frontend'),
            static_folder=os.path.join(PROJECT_DIR, 'static'))

# Configuration using relative paths (Render‐friendly)
UPLOAD_FOLDER = os.path.join('/mnt/data', 'uploads')
PROCESSED_FOLDER = os.path.join('/mnt/data', 'processed')
DATA_FOLDER = '/mnt/data'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER
app.config['DATA_FOLDER'] = DATA_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# Create directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)
os.makedirs(DATA_FOLDER, exist_ok=True)

# Fixed processed filename and products JSON path
PROCESSED_FILENAME = "processed_Price_Matching.xlsx"
PRODUCTS_JSON_PATH = os.path.join(DATA_FOLDER, "products.json")

# Define primary storage path for product data using relative paths
PRIMARY_STORAGE_PATH = os.path.join('/mnt/data', 'product_data.json')

# Replace the DROPBOX_ACCESS_TOKEN constant with these constants
DROPBOX_APP_KEY = "bcvvobmq9urp9b3"  # Replace with your Dropbox app key
DROPBOX_APP_SECRET = "bq3ggjy0v47iymw"  # Replace with your Dropbox app secret
DROPBOX_REFRESH_TOKEN = "CrdI_N2hNvYAAAAAAAAAASoQHawJmRyadHGL1NB-oTNmLS9QvBumYrgV348_piiw"  # Replace with your refresh token
DROPBOX_ACCESS_TOKEN = "sl.u.AFpsH7k3VMIbzyBPuJB0BxaUElIQbgBc-ZpRy_x9Q91cJsRLQmUJUBVWa5KQ5hdUQG1e6hi8mmqLPMTzXdKwIFft3cH_kIVFZM287i3g2_in1OdBBHS_rSZwDtaec_tarEdqUhy5T5tSfchG5N-lHtEkb5ql9nr1AGOXJqv00cQucbjDzsD6C2PbnRr-CUXRiZM5JCrnaI9CnyOtFcRuPOueA6rAApRolcxwJ9FcLRWNLT8kBpV4KWpau24UXVuVVAga6Cgm4er4RTTwHAraL6BxPfToNqktA9yuf7JzemrER0mkbHbWmJvVVm4N7CMDvDl-uZjizA7ci_M4ZZ74DqVV-4nOMfIOQAY7RRY03ECyCb7hX88fzAXjyxBH3iPcXonVzStujOqTqAkCCdErnoIm7odUrN6YGqAAUyn5_u2iKijno9i4O22pZAKFZR0UIltWk-bbMTemrzp9W2BXAEXiLFWKYynkdQlf6bo-CH8kW7zeLwnv6qcQxp1STlURP92d6b58HSf6PpzqB2STHC8cG7RZ5v00hRc3eR1oZ0jUUdmXFhDG5EF0GKmDOj1wT_4v8hR93qZsPFa4SJI9e0tOA_nWB0ZE7hlaWxBfpG0W7PpekhBmk7a-fuIBYlN_v-qbxiExhvfP3PeT3r3yKJidZCqkVRQk3G6hbuweUXpzeG2iInx9dVcRmUdDpYSky2xZVFHOdShyTA36o0yPWTFBfMyqJ9d0KKOXgkZPl4XMlk-C6H94vl2LhD_0oJvdngB7_fyI4WAFZaryu2c7-LZYf1pXN3mcVxt2nyOXUUHkB1ePD8iM5Jl0AK_lTXw3rs38Xle6kt5MWthiTUyhNTTRBOOERNTH2eanYmx3PZgT1Mynk6YnzYI_hUl3NJmgCd91Il34QrG_-pjNzE6OAM3E-NOaH1XmqXT58Qp7MOmx6jFFYRBPhGA-tez31CfMY9WrMHzh0z1QFztvvUSmELg-rjwt9HhCN-onHq1-6II_2QPYLEIvJrOiwZ2Si2sAXjChQmdVCjZTDVfR5G-4lhHsYGdT0qAOZH1Yv2W3ho7hsP_Wd836rgCWPv4x9PghZG5k4IpgO8iUsACxOny284FNrgPol9Aw1rT_l9VOAYY01dIcPA448Daicwq6FEAVvWFzGP_KbrMPTpdKEi6BhpgHcPLxnIaTbxqA2HkTe28PAJ3JH2sXAEglahRieMkC9YvchBuT3WbwJwHHfMBqo8ii8Dx6Z0GvDNM76xOGTZSZJcnDle6PygncvMe0Ix9aP3Kgmd2IevZYsxPkX1ekGn5cN96lBCdZM_GMn0ZNwkd71_0KQsWt6XBpUX0ebFCV5_u352qN_Yd7RX6CqFiKcfD_YEOe7iI010lIDA4vWrF9H1T-RLNVBG84fWkFlv60L1SGP9ulLwYa5blUXHS2HD5H"  # Keep this for initial use
DROPBOX_FOLDER = "/PriceExports"  # Keep your existing folder path

def get_storage_path():
    # Use primary storage if its directory is writable; otherwise, use data folder
    primary_dir = os.path.dirname(PRIMARY_STORAGE_PATH)
    if os.path.exists(primary_dir) and os.access(primary_dir, os.W_OK):
        return PRIMARY_STORAGE_PATH
    else:
        # Use the DATA_FOLDER which is already set up with proper relative paths
        fallback_path = os.path.join(DATA_FOLDER, "product_data.json")
        return fallback_path

# Import scraper configurations from API
SCRAPER_DIR = os.path.join(PROJECT_DIR, "scrapers")

# Define a list of rotating user agents and headers
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0"
]

ACCEPT_HEADERS = [
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
]

ACCEPT_LANGUAGE_HEADERS = [
    "en-GB,en;q=0.9",
    "en-GB,en-US;q=0.9,en;q=0.8",
    "en-GB,en;q=0.8",
    "en-US,en-GB;q=0.9,en;q=0.8"
]

# Mapping from domain to scraper module/file and function
DOMAIN_SCRAPERS = {
    "andertons.co.uk": {
        "file": os.path.join(SCRAPER_DIR, "app_Andertons.py"),
        "function": "scrape_andertons_price"
    },
    "bonnersmusic.co.uk": {
        "file": os.path.join(SCRAPER_DIR, "app_Bonners.py"),
        "function": "scrape_bonners_price"
    },
    "musicmatter.co.uk": {
        "file": os.path.join(SCRAPER_DIR, "app_MusicMatters.py"),
        "function": "scrape_musicmatter_price"
    },
    "guitarguitar.co.uk": {
        "file": os.path.join(SCRAPER_DIR, "app_GG.py"),
        "function": "scrape_guitarguitar_price"
    },
    "gak.co.uk": {
        "file": os.path.join(SCRAPER_DIR, "app_GAK.py"),
        "function": "scrape_gak_price"
    },
    "pmtonline.co.uk": {
        "file": os.path.join(SCRAPER_DIR, "app_PMT.py"),
        "function": "scrape_pmt_price"
    },
    "rimmersmusic.co.uk": {
        "file": os.path.join(SCRAPER_DIR, "app_Rimmers.py"),
        "function": "scrape_rimmers_price"
    },
    "gear4music.com": {
        "file": os.path.join(SCRAPER_DIR, "app_Gear4Music.py"),
        "function": "scrape_gear4music_price"
    }
}

def extract_domain(url):
    match = re.search(r'https?://(?:www\.)?([^/]+)', url)
    return match.group(1) if match else None

def load_module(file_path, module_name):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

@app.route('/')
def index():
    print(f"Template folder: {app.template_folder}")
    print(f"Looking for template: importt.html")
    print(f"Full path: {os.path.join(app.template_folder, 'importt.html')}")
    print(f"File exists: {os.path.exists(os.path.join(app.template_folder, 'importt.html'))}")
    return render_template('importt.html')

@app.route('/scrape-price', methods=['POST'])
def scrape_price():
    data = request.json
    url = data.get("url")
    if not url:
        return jsonify({"error": "URL is required"}), 400

    domain = extract_domain(url)
    if not domain:
        return jsonify({"error": "Invalid URL format"}), 400

    matched_scraper = None
    for known_domain, scraper_info in DOMAIN_SCRAPERS.items():
        if known_domain in domain:
            module_path = scraper_info["file"]
            func_name = scraper_info["function"]
            if os.path.exists(module_path):
                try:
                    module_name = os.path.basename(module_path).replace(".py", "")
                    module = load_module(module_path, module_name)
                    matched_scraper = getattr(module, func_name)
                except Exception as e:
                    return jsonify({"error": f"Failed to load scraper for {domain}: {str(e)}"}), 500
            break

    if not matched_scraper:
        return jsonify({"error": f"No scraper found for {domain}"}), 404

    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": random.choice(ACCEPT_HEADERS),
        "Accept-Language": random.choice(ACCEPT_LANGUAGE_HEADERS)
    }

    try:
        print(f"Calling scraper for {url}")
        result = matched_scraper(url, headers=headers)
        print(f"Scraper returned: {result}")
        # Use UTC+1 (BST) for the timestamp
        current_time = datetime.now(timezone(timedelta(hours=1))).isoformat()
        if result is None:
            return jsonify({
                "url": url,
                "domain": domain,
                "price": "Not found",
                "stock": "Unknown",
                "timestamp": current_time
            })
        if isinstance(result, dict):
            price = result.get("price", "Not found")
            stock = result.get("stock", "Unknown")
        else:
            price = result if result else "Not found"
            stock = "Unknown"
        response_data = {
            "url": url,
            "domain": domain,
            "price": price,
            "stock": stock,
            "timestamp": current_time
        }
        print(f"Returning timestamp: {current_time}")  # Debug log
        return jsonify(response_data)
    except Exception as e:
        return jsonify({"error": f"Scraping failed: {str(e)}"}), 500

@app.route('/api/products', methods=['GET'])
def get_products():
    try:
        storage_path = get_storage_path()
        if os.path.exists(storage_path):
            with open(storage_path, 'r') as f:
                data = json.load(f)
                # Add debugging to check timestamps
                print("Sending data to frontend with timestamps:")
                for product in data:
                    for url_obj in product.get("urls", []):
                        if "lastUpdate" in url_obj:
                            print(f"URL: {url_obj.get('url')} - lastUpdate: {url_obj.get('lastUpdate')}")
        else:
            data = []
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/products', methods=['POST'])
def save_products():
    try:
        products = request.json
        if not isinstance(products, list):
            return jsonify({"error": "Data must be a list of product objects"}), 400

        storage_path = get_storage_path()
        if os.path.exists(storage_path):
            backup_path = storage_path + '.bak.' + datetime.now().strftime("%Y%m%d%H%M%S")
            os.rename(storage_path, backup_path)
        with open(storage_path, 'w') as f:
            json.dump(products, f, indent=4)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/products/auto-save', methods=['POST'])
def auto_save_products():
    try:
        products = request.json
        if not isinstance(products, list):
            return jsonify({"error": "Data must be a list of product objects"}), 400

        storage_path = get_storage_path()
        with open(storage_path, 'w') as f:
            json.dump(products, f, indent=4)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -----------------------------
# Periodic Price Update Section
# -----------------------------
def update_all_prices():
    """Run price update for all products"""
    storage_path = get_storage_path()
    if not os.path.exists(storage_path):
        print("No product data found.")
        return
        
    with open(storage_path, 'r') as f:
        products = json.load(f)
    
    for product in products:
        if product.get("urls"):
            update_prices_for_product(product)
    
    # Always save to persist lastUpdate timestamps, even if no prices changed
    with open(storage_path, 'w') as f:
        json.dump(products, f, indent=2)
    print("Product data saved with updated timestamps.")
    
    # Try to export to Dropbox after updating
    try:
        export_to_dropbox()
        print("Daily export to Dropbox completed successfully.")
    except Exception as e:
        print(f"Error in automatic export to Dropbox: {str(e)}")

def export_to_dropbox():
    """Create export file and upload to Dropbox (without browser download)"""
    try:
        storage_path = get_storage_path()
        if not os.path.exists(storage_path):
            raise Exception("No product data found")
            
        with open(storage_path, 'r') as f:
            products = json.load(f)
        
        # Sort products alphabetically by product name
        sorted_products = sorted(products, key=lambda x: x.get("productName", "").lower())
        
        # Create a memory file for the CSV
        csv_data = StringIO()
        writer = csv.writer(csv_data, dialect='excel', quoting=csv.QUOTE_MINIMAL)
        
        # Write header row
        writer.writerow(["Product Name", "Product Code", "Competitor URL", "Competitor Price", "Date Scraped"])
        
        # Write each product-competitor pair as a separate row
        for product in sorted_products:
            product_name = product.get("productName", "N/A")
            
            # Format product code with Excel's text formula to preserve leading zeros
            raw_product_code = str(product.get("productCode", "N/A"))
            # Use Excel's text formula format: ="001234"
            product_code = f'="{raw_product_code}"'
            
            # If a product has no URLs, still include one row for the product
            if not product.get("urls") or len(product.get("urls", [])) == 0:
                writer.writerow([product_name, product_code, "", "", ""])
                continue
            
            # Add a separate row for each competitor URL
            for url_obj in product.get("urls", []):
                url = url_obj.get("url", "")
                price = url_obj.get("price", "")
                
                # Format the date (if available)
                last_update = url_obj.get("lastUpdate", "")
                formatted_date = ""
                if last_update:
                    try:
                        update_date = datetime.fromisoformat(last_update)
                        formatted_date = update_date.strftime('%Y-%m-%d')
                    except ValueError:
                        formatted_date = last_update
                
                # Write this product-competitor pair as a row
                writer.writerow([product_name, product_code, url, price, formatted_date])
        
        # Get the CSV data as a string and encode to bytes
        csv_bytes = csv_data.getvalue().encode('utf-8')
        
        # Create a BytesIO object for Dropbox upload
        mem_file = BytesIO(csv_bytes)
        
        # Create filename with new format
        filename = f"prices{datetime.now().strftime('%Y-%m-%d')}.csv"
        
        # Upload to Dropbox
        dropbox_path = f"{DROPBOX_FOLDER}/{filename}"
        print(f"Uploading to Dropbox: {dropbox_path}")
        
        if not upload_to_dropbox(mem_file, dropbox_path):
            raise Exception("Failed to upload to Dropbox")
        
        print(f"Successfully uploaded to Dropbox: {dropbox_path}")
        return True
        
    except Exception as e:
        print(f"Dropbox export error: {str(e)}")
        raise e

def run_periodic_price_update():
    while True:
        # Get current time in UK timezone (GMT/BST)
        uk_time = datetime.now(timezone(timedelta(hours=1)))  # UTC+1 for BST, or use 0 for GMT
        
        # Calculate time until next 5am
        target_hour = 5
        if uk_time.hour >= target_hour:
            # If it's already past 5am, wait until 5am tomorrow
            next_run = uk_time.replace(day=uk_time.day+1, hour=target_hour, minute=0, second=0, microsecond=0)
        else:
            # If it's before 5am, wait until 5am today
            next_run = uk_time.replace(hour=target_hour, minute=0, second=0, microsecond=0)
        
        # Calculate seconds to sleep
        sleep_seconds = (next_run - uk_time).total_seconds()
        
        print(f"Scheduled next price update at {next_run.strftime('%Y-%m-%d %H:%M:%S')} UK time")
        print(f"Sleeping for {sleep_seconds/3600:.2f} hours")
        
        # Sleep until next run time
        time.sleep(sleep_seconds)
        
        # Run the update
        update_all_prices()
        print(f"Completed price update at {datetime.now(timezone(timedelta(hours=1))).strftime('%Y-%m-%d %H:%M:%S')} UK time")

# Comment out these lines to disable scraping
price_update_thread = threading.Thread(target=run_periodic_price_update, daemon=True)
price_update_thread.start()

@app.route('/api/export', methods=['GET'])
def export_products():
    try:
        storage_path = get_storage_path()
        if not os.path.exists(storage_path):
            return jsonify({"error": "No product data found"}), 404
            
        with open(storage_path, 'r') as f:
            products = json.load(f)
        
        # Sort products alphabetically by product name (for grouping)
        sorted_products = sorted(products, key=lambda x: x.get("productName", "").lower())
        
        # Create a memory file for the CSV
        csv_data = StringIO()
        writer = csv.writer(csv_data, dialect='excel', quoting=csv.QUOTE_MINIMAL)
        
        # Write header row
        writer.writerow(["Product Name", "Product Code", "Competitor URL", "Competitor Price", "Date Scraped"])
        
        # Write each product-competitor pair as a separate row (in alphabetical order)
        for product in sorted_products:
            product_name = product.get("productName", "N/A")
            
            # Format product code with Excel's text formula to preserve leading zeros
            raw_product_code = str(product.get("productCode", "N/A"))
            # Use Excel's text formula format: ="001234"
            product_code = f'="{raw_product_code}"'
            
            # If a product has no URLs, still include one row for the product
            if not product.get("urls") or len(product.get("urls", [])) == 0:
                writer.writerow([product_name, product_code, "", "", ""])
                continue
            
            # Add a separate row for each competitor URL
            for url_obj in product.get("urls", []):
                url = url_obj.get("url", "")
                price = url_obj.get("price", "")
                
                # Format the date (if available)
                last_update = url_obj.get("lastUpdate", "")
                formatted_date = ""
                if last_update:
                    try:
                        update_date = datetime.fromisoformat(last_update)
                        formatted_date = update_date.strftime('%Y-%m-%d')
                    except ValueError:
                        formatted_date = last_update
                
                # Write this product-competitor pair as a row
                writer.writerow([product_name, product_code, url, price, formatted_date])
        
        # Get the CSV data as a string and encode to bytes
        csv_bytes = csv_data.getvalue().encode('utf-8')
        
        # Create a BytesIO object for download
        download_file = BytesIO(csv_bytes)
        
        # Create filename with new format
        filename = f"prices{datetime.now().strftime('%Y-%m-%d')}.csv"
        
        # Also upload to Dropbox
        try:
            dropbox_path = f"{DROPBOX_FOLDER}/{filename}"
            print(f"Uploading to Dropbox from export_products: {dropbox_path}")
            
            # Create a separate BytesIO for Dropbox upload
            dropbox_file = BytesIO(csv_bytes)
            upload_successful = upload_to_dropbox(dropbox_file, dropbox_path)
            
            if upload_successful:
                print(f"Successfully uploaded to Dropbox: {dropbox_path}")
            else:
                print("Dropbox upload failed")
        except Exception as e:
            print(f"Dropbox upload error: {str(e)}")
            # Continue with download even if Dropbox upload fails
        
        # Return the CSV as a downloadable file
        return send_file(
            download_file,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"Export error: {str(e)}")
        return jsonify({"error": f"Export failed: {str(e)}"}), 500

def get_dropbox_client():
    """Get a Dropbox client with auto-refresh capability"""
    try:
        # Try using the access token
        dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)
        # Test if token is valid
        dbx.users_get_current_account()
        return dbx
    except AuthError:
        # Token expired, try to refresh
        try:
            print("Access token expired. Attempting to refresh...")
            
            # Use refresh token to get a new access token
            refresh_url = "https://api.dropboxapi.com/oauth2/token"
            data = {
                "grant_type": "refresh_token",
                "refresh_token": DROPBOX_REFRESH_TOKEN,
                "client_id": DROPBOX_APP_KEY,
                "client_secret": DROPBOX_APP_SECRET
            }
            
            response = requests.post(refresh_url, data=data)
            if response.status_code == 200:
                token_data = response.json()
                new_access_token = token_data.get("access_token")
                print("Successfully refreshed access token")
                
                # Create a new client with the refreshed token
                return dropbox.Dropbox(new_access_token)
            else:
                print(f"Failed to refresh token. Status code: {response.status_code}")
                print(f"Response: {response.text}")
                raise Exception("Token refresh failed")
        except Exception as e:
            print(f"Failed to refresh token: {e}")
            raise

def upload_to_dropbox(file_obj, dropbox_path):
    """Upload a file to Dropbox with token refresh capability"""
    try:
        # Get a client with auto-refresh
        dbx = get_dropbox_client()
        
        # Upload the file
        file_obj.seek(0)  # Make sure we're at the beginning
        dbx.files_upload(
            file_obj.read(),
            dropbox_path,
            mode=WriteMode.overwrite
        )
        
        print(f"Successfully uploaded file to Dropbox: {dropbox_path}")
        return True
    except AuthError as e:
        print(f"Dropbox authentication error: {e}")
        return False
    except ApiError as e:
        print(f"Dropbox API error: {e}")
        return False
    except Exception as e:
        print(f"Dropbox upload error: {e}")
        return False

def update_prices_for_product(product):
    """Update prices for all URLs of a single product"""
    updated = False
    if not product.get("urls"):
        return updated
    
    for url_obj in product.get("urls", []):
        url = url_obj.get("url")
        if not url:
            continue
            
        try:
            # Extract domain from URL
            domain = extract_domain(url)
            if not domain:
                print(f"Invalid URL format: {url}")
                continue
                
            # Find matching scraper
            matched_scraper = None
            for known_domain, scraper_info in DOMAIN_SCRAPERS.items():
                if known_domain in domain:
                    module_path = scraper_info["file"]
                    func_name = scraper_info["function"]
                    if os.path.exists(module_path):
                        try:
                            module_name = os.path.basename(module_path).replace(".py", "")
                            module = load_module(module_path, module_name)
                            matched_scraper = getattr(module, func_name)
                            break
                        except Exception as e:
                            print(f"Failed to load scraper for {domain}: {str(e)}")
                            continue
            
            if not matched_scraper:
                print(f"No scraper found for {domain}")
                continue
                
            # Generate random headers
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": random.choice(ACCEPT_HEADERS),
                "Accept-Language": random.choice(ACCEPT_LANGUAGE_HEADERS)
            }
            
            # Scrape the price
            print(f"Scraping price for {url}")
            url_obj["lastUpdate"] = datetime.now().isoformat()  # Always update timestamp
            result = matched_scraper(url, headers=headers)
            
            # Extract price and stock information
            if result is None:
                continue
                
            if isinstance(result, dict):
                price = result.get("price")
                stock = result.get("stock", "Unknown")
            else:
                price = result
                stock = "Unknown"
                
            # Update if price changed
            if price and price != url_obj.get("price"):
                url_obj["price"] = price
                url_obj["stock"] = stock
                updated = True
                print(f"Updated price for {product.get('productName')} ({url}): {price}")
            else:
                print(f"No price change for {product.get('productName')} ({url})")
                
        except Exception as e:
            print(f"Error updating price for {url}: {str(e)}")
            url_obj["lastUpdate"] = datetime.now().isoformat()  # Update timestamp even on failure
            updated = True
    
    return updated

def update_price_for_url(product_index, url_index):
    """Update price for a specific URL of a product"""
    try:
        # Load products
        storage_path = get_storage_path()
        with open(storage_path, 'r') as f:
            products = json.load(f)
        
        # Get the product and URL
        product = products[product_index]
        url_obj = product["urls"][url_index]
        url = url_obj["url"]
        
        # Scrape the price
        price = scrape_price(url)
        
        # Always update the timestamp, regardless of price change
        url_obj["lastUpdate"] = datetime.now().isoformat()
        
        if price:
            # Check if price has changed
            old_price = url_obj.get("price", "")
            price_changed = (old_price != price)
            
            # Update the price
            url_obj["price"] = price
            
            # Save the updated products
            with open(storage_path, 'w') as f:
                json.dump(products, f, indent=2)
            
            if price_changed:
                print(f"Updated price for {url}: {old_price} -> {price}")
            else:
                print(f"Price unchanged for {url}: {price}")
            
            return True
        else:
            # Still save the updated timestamp even if price scraping failed
            print(f"Failed to scrape price for {url}")
            
            # Save the updated products with the new timestamp
            with open(storage_path, 'w') as f:
                json.dump(products, f, indent=2)
            
            return False
    except Exception as e:
        print(f"Error updating price: {str(e)}")
        return False

@app.route('/api/products/validate-code', methods=['POST'])
def validate_product_code():
    try:
        data = request.json
        product_code = data.get('productCode')
        
        if not product_code:
            return jsonify({"valid": True})  # Empty codes are allowed
        
        # Get the storage path and check if the file exists
        storage_path = get_storage_path()
        if not os.path.exists(storage_path):
            return jsonify({"valid": True})  # No products file exists yet
        
        # Read the products from the file
        with open(storage_path, 'r') as f:
            products = json.load(f)
        
        # Check if the product code already exists
        for product in products:
            if product.get('productCode') == product_code:
                return jsonify({"valid": False, "message": "Product code already exists"})
        
        # If we get here, the code is valid
        return jsonify({"valid": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', debug=False, port=port)