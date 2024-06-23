# app/routes.py

from flask import render_template, request, redirect, url_for, send_file, flash, current_app
from . import db
from app.models import AirbnbReview
from .services.data_cleaning import load_config, clean_airbnb_data, save_data
from .services.airbnb_apify import fetch_airbnb_data
import json
import os
import pandas as pd
import threading
import logging

logging.basicConfig(level=logging.INFO)

@app.route('/')
def index():
    """
    Display the main page with the form for user input.
    Load the current configuration from config.json.
    """
    config_path = os.path.join(current_app.root_path, 'config.json')
    config = load_config(config_path)
    return render_template('index.html', config=config)

@app.route('/submit', methods=['POST'])
def submit():
    """
    Handle form submission.
    Update the config.json file with new values from the form.
    Redirect back to the index page.
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
    return redirect(url_for('index'))

def run_cleaning_process(config, airbnb_data):
    """
    Run the data cleaning process.
    Save cleaned data back to the database and generate the output file.
    """
    cleaned_df = clean_airbnb_data(airbnb_data, config)
    output_directory = config['General']['output_directory']
    output_file_name = f"{config['General']['output_file_name']}.{config['General']['output_file_format']}"
    output_file_path = os.path.join(output_directory, output_file_name)
    save_data(cleaned_df, config)

    # Save cleaned data back to the database
    for index, row in cleaned_df.iterrows():
        review = AirbnbReview(
            listing_name=row['Listing Name'],
            review_date=row['review_date'],
            review_text=row['review_text'],
            user_name=row['user_name'],
            rating=row['rating'],
            created_at=row['created_at']
        )
        db.session.add(review)
    db.session.commit()

    logging.info("Data cleaning process completed and saved to database.")
    return output_file_path

@app.route('/run_cleaning', methods=['POST'])
def run_cleaning():
    """
    Fetch data from Airbnb API based on config and run the cleaning process.
    Redirect to the loading page while the process runs.
    """
    config_path = os.path.join(current_app.root_path, 'config.json')
    config = load_config(config_path)

    # Fetch data from Airbnb API
    airbnb_data = fetch_airbnb_data(config)

    if not airbnb_data:
        flash("Failed to fetch data from Airbnb API.")
        logging.error("Failed to fetch data from Airbnb API.")
        return redirect(url_for('index'))

    # Run cleaning process in a separate thread
    cleaning_thread = threading.Thread(target=run_cleaning_process, args=(config, airbnb_data))
    cleaning_thread.start()

    logging.info("Data cleaning process started.")
    return redirect(url_for('loading'))

@app.route('/loading')
def loading():
    """
    Display the loading page while the data cleaning process runs.
    """
    return render_template('loading.html')

@app.route('/download')
def download():
    """
    Allow the user to download the output file after the data cleaning process completes.
    """
    config_path = os.path.join(current_app.root_path, 'config.json')
    config = load_config(config_path)
    output_directory = config['General']['output_directory']
    output_file_name = f"{config['General']['output_file_name']}.{config['General']['output_file_format']}"
    output_file_path = os.path.join(output_directory, output_file_name)
    
    return send_file(output_file_path, as_attachment=True)
