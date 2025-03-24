import os
import json
import uuid
import pandas as pd
import subprocess
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
import threading
import time

app = Flask(__name__)

# Configuration using relative paths (Render‐friendly)
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Create directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# Fixed processed filename
PROCESSED_FILENAME = "processed_Price_Matching.xlsx"

# Global variables to track scraping progress
scraping_in_progress = False
scraping_progress = 0
scraping_total = 0
scraping_message = ""

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('importt.html')

def run_scraper():
    global scraping_in_progress, scraping_progress, scraping_total, scraping_message

    scraping_in_progress = True
    scraping_progress = 0
    scraping_total = 100  # Initial estimate; will be updated based on output
    scraping_message = "Starting price scraping..."

    try:
        # Use a relative path for the controller file
        controller_path = os.path.join(os.getcwd(), "app_controller.py")
        process = subprocess.Popen(
            ["python3", controller_path, "--all"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )

        # Process the scraper's output line by line
        for line in process.stdout:
            line = line.strip()
            print(f"Scraper output: {line}")
            if "Found" in line and "URLs to process" in line:
                try:
                    scraping_total = int(line.split("Found ")[1].split(" URLs")[0])
                    scraping_message = f"Found {scraping_total} URLs to process"
                except Exception:
                    pass
            elif "Scraping:" in line:
                try:
                    progress_part = line.split("|")[0].split(":")[1].strip()
                    if "%" in progress_part:
                        percent = int(progress_part.split("%")[0])
                        scraping_progress = (percent * scraping_total) // 100
                        scraping_message = f"Scraping URLs: {percent}% complete"
                except Exception:
                    pass
            elif "Saving progress after" in line:
                try:
                    scraping_progress = int(line.split("after ")[1].split(" URLs")[0])
                    scraping_message = f"Saved progress: {scraping_progress}/{scraping_total} URLs processed"
                except Exception:
                    pass
            elif "Done! Processed" in line:
                try:
                    scraping_progress = int(line.split("Processed ")[1].split(" URLs")[0])
                    scraping_message = f"Completed: {scraping_progress} URLs processed"
                except Exception:
                    pass

        process.wait()
        scraping_message = "Price scraping completed successfully!"
    except Exception as e:
        scraping_message = f"Error during scraping: {str(e)}"
    finally:
        scraping_in_progress = False

@app.route('/api/import', methods=['POST'])
def import_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    # Get import type and mappings from form data
    import_type = request.form.get('importType', '')
    mappings_json = request.form.get('mappings', '[]')
    try:
        mappings = json.loads(mappings_json)
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid mappings format'}), 400

    # Generate a unique filename for the uploaded file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_id = str(uuid.uuid4())[:8]
    original_filename = secure_filename(file.filename)
    filename_parts = original_filename.rsplit('.', 1)
    new_filename = f"{filename_parts[0]}_{timestamp}_{unique_id}.{filename_parts[1]}"

    original_file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
    file.save(original_file_path)

    try:
        # Read the Excel file
        df = pd.read_excel(original_file_path)
        # Create new DataFrame using mapped columns
        new_df = pd.DataFrame()
        for mapping in mappings:
            if mapping.get('included', True):
                original_col = mapping['originalColumn']
                mapped_to = mapping['mappedTo']
                if original_col in df.columns:
                    new_df[mapped_to] = df[original_col]
        # Debug: log the mapped columns
        print("Mapped columns in processed file:", list(new_df.columns))

        # Ensure that all expected competitor URL columns exist—even if empty
        from app_controller import DOMAIN_SCRAPERS  # Import the mapping dict from your controller
        for spec in DOMAIN_SCRAPERS.values():
            comp_col = spec["url_column"]
            if comp_col not in new_df.columns:
                print(f"Creating missing competitor column: {comp_col}")
                new_df[comp_col] = None

        processed_file_path = os.path.join(app.config['PROCESSED_FOLDER'], PROCESSED_FILENAME)
        new_df.to_excel(processed_file_path, index=False)
        records_processed = len(new_df)

        # Start the scraper in a background thread
        threading.Thread(target=run_scraper).start()

        return jsonify({
            'success': True,
            'fileName': PROCESSED_FILENAME,
            'recordsProcessed': records_processed,
            'importType': import_type,
            'scrapingStarted': True,
            'redirect': True,
            'redirectUrl': url_for('scraping_progress_page')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/scraping-progress')
def get_scraping_progress():
    global scraping_in_progress, scraping_progress, scraping_total, scraping_message
    return jsonify({
        'inProgress': scraping_in_progress,
        'progress': scraping_progress,
        'total': scraping_total,
        'message': scraping_message
    })

@app.route('/download')
def download_file():
    return send_from_directory(app.config['PROCESSED_FOLDER'], PROCESSED_FILENAME, as_attachment=True)

@app.route('/dashboard')
def dashboard():
    return "Dashboard Page"

@app.route('/products')
def products():
    return "Products Page"

@app.route('/import_log')
def import_log():
    return "Import Log Page"

@app.route('/scraping_progress')
def scraping_progress_page():
    return render_template('scraping_progress.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5001)