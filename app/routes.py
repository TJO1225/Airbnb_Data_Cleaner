# app/routes.py

from flask import Blueprint, render_template, request, redirect, url_for, send_file, flash, current_app
from . import db
from .models import AirbnbReview
from .services.data_cleaning import load_config, clean_airbnb_data, save_data
from .services.airbnb_apify import fetch_airbnb_data
import json
import os
import pandas as pd
import threading
import logging

logging.basicConfig(level=logging.INFO)

# Create a blueprint
bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """
    Display the main page with the form for user input.
    Load the current configuration from config.json.
    """
    config_path = os.path.join(current_app.root_path, 'config.json')
    config = load_config(config_path)
    return render_template('index.html', config=config)

@bp.route('/run_cleaning', methods=['POST'])
def run_cleaning():
    """
    Handle form submission, save configuration, fetch data from Airbnb API, and run the cleaning process.
    Redirect to the loading page while the process runs.
    """
    form_data = request.form.to_dict()
    config_path = os.path.join(current_app.root_path, 'config.json')

    with open(config_path, 'r') as f:
        config = json.load(f)

    # Update the config with form data
    for key, value in form_data.items():
        if key in config['Search Variables']:
            config['Search Variables'][key] = value
        elif key in config['Logic Variables']['Good Data']:
            config['Logic Variables']['Good Data'][key] = value
        elif key in config['Logic Variables']['Possibly Good Data']:
            config['Logic Variables']['Possibly Good Data'][key] = value
        elif key in config['General']:
            config['General'][key] = value

    # Save the updated config
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)

    logging.info("Configuration updated successfully.")

    # Fetch data from Airbnb API
    airbnb_data = fetch_airbnb_data(config)

    if not airbnb_data:
        flash("Failed to fetch data from Airbnb API.")
        logging.error("Failed to fetch data from Airbnb API.")
        return redirect(url_for('main.index'))

    # Run cleaning process in a separate thread
    cleaning_thread = threading.Thread(target=run_cleaning_process, args=(config, airbnb_data))
    cleaning_thread.start()

    logging.info("Data cleaning process started.")
    return redirect(url_for('main.loading'))

def run_cleaning_process(config, airbnb_data):
    """
    Run the data cleaning process.
    Save cleaned data back to the database and generate the output file.
    """
    # Clean the data
    cleaned_df = clean_airbnb_data(airbnb_data, config)
    
    # Save cleaned data to database and generate output file
    output_file_path = save_data(cleaned_df, config)
    
    logging.info("Data cleaning process completed and saved to database.")
    
    # After processing, store the file path in a session variable or similar mechanism
    current_app.config['output_file_path'] = output_file_path

@bp.route('/loading')
def loading():
    """
    Display the loading page while the data cleaning process runs.
    """
    return render_template('loading.html')

@bp.route('/check_processing', methods=['GET'])
def check_processing():
    """
    Check if the processing is complete.
    """
    if os.path.exists('processing_complete.txt'):
        return redirect(url_for('main.download'))
    return redirect(url_for('main.loading'))

@bp.route('/download')
def download():
    """
    Allow the user to download the output file after the data cleaning process completes.
    """
    output_file_path = current_app.config.get('output_file_path')
    
    if output_file_path and os.path.exists(output_file_path):
        return send_file(output_file_path, as_attachment=True)
    else:
        flash("File not found.")
        return redirect(url_for('main.index'))

