# app/routes.py

from flask import Blueprint, render_template, request, redirect, url_for, send_from_directory, flash, current_app
from app.services.data_cleaning import load_config, clean_airbnb_data, save_data
from app.services.airbnb_apify import fetch_airbnb_data
import os
import threading
import logging
import json
from werkzeug.utils import secure_filename

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
    form_data = request.form.to_dict()
    logging.info(f"Form data received: {form_data}")  # Log form data for debugging

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
        elif key == 'output_file_format':
            config['General']['output_file_format'] = 'xlsx' if value == 'excel' else 'csv'
        elif key == 'output_file_name':
            config['General']['output_file_name'] = value
        elif key in config['General']:
            config['General'][key] = value

    # Save the updated config and log it
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)
    logging.info(f"Updated config: {config}")  # Log updated config for debugging

    logging.info("Configuration updated successfully.")

    # Redirect to the loading page immediately
    response = redirect(url_for('main.loading'))

    # Start the data fetching and cleaning process in a separate thread
    def background_task(app_context, config):
        with app_context:
            airbnb_data = fetch_airbnb_data(config)
            if not airbnb_data:
                logging.error("Failed to fetch data from Airbnb API.")
                return

            output_file_name = secure_filename(config['General']['output_file_name'])
            output_file_format = config['General']['output_file_format']
            temp_dir = current_app.config['TEMP_DIR']
            output_file_path = os.path.join(temp_dir, f"{output_file_name}.{output_file_format}")

            run_cleaning_process(config, airbnb_data, output_file_path, output_file_format)

            current_app.config['output_file_path'] = output_file_path
            current_app.config['processing_complete'] = True

    app_context = current_app.app_context()
    cleaning_thread = threading.Thread(target=background_task, args=(app_context, config))
    cleaning_thread.start()

    logging.info("Data cleaning process started.")
    return response



def run_cleaning_process(config, airbnb_data, output_file_path, output_file_format):
    logging.info("Starting data cleaning process.")
    
    with current_app.app_context():
        try:
            cleaned_df = clean_airbnb_data(airbnb_data, config)
            logging.info("Data cleaning process completed.")
            
            save_data(cleaned_df, output_file_path, output_file_format)
            logging.info(f"File successfully saved: {output_file_path}")
            
            current_app.config['output_file_path'] = output_file_path
            logging.info(f"Output file path set: {output_file_path}")
            
            # Signal success for redirection to download page
            with current_app.test_request_context():
                current_app.config['processing_complete'] = True

        except Exception as e:
            logging.error(f"Error during data cleaning process: {e}", exc_info=True)
            with current_app.test_request_context():
                current_app.config['processing_complete'] = False




@bp.route('/loading')
def loading():
    """
    Display the loading page while the data cleaning process runs.
    """
    if current_app.config.get('processing_complete'):
        return redirect(url_for('main.download'))
    return render_template('loading.html')


@bp.route('/check_processing', methods=['GET'])
def check_processing():
    """
    Check if the processing is complete.
    """
    if current_app.config.get('output_file_path'):
        return redirect(url_for('main.download'))
    return redirect(url_for('main.loading'))

@bp.route('/download')
def download():
    """
    Allow the user to download the output file after the data cleaning process completes.
    """
    output_file_path = current_app.config.get('output_file_path')
    filename = os.path.basename(output_file_path) if output_file_path else None
    
    if filename and os.path.exists(output_file_path):
        return send_from_directory(directory=current_app.config['TEMP_DIR'], filename=filename, as_attachment=True)
    else:
        flash("File not found.")
        return redirect(url_for('main.index'))

