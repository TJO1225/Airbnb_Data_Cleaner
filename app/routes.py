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

@bp.route('/update_config', methods=['POST'])
def update_config():
    form_data = request.form.to_dict()
    logging.info(f"Form data received: {form_data}")

    # Retrieve output file name from form data and generate config file name
    output_file_name = form_data.get('output_file_name', 'default_output')
    config_filename = f"{output_file_name}.config"
    config_path = os.path.join(current_app.config['TEMP_DIR'], config_filename)

    # Load the default configuration from the base config.json file to update
    default_config_path = os.path.join(current_app.root_path, 'config.json')
    try:
        with open(default_config_path, 'r') as f:
            config = json.load(f)
    except IOError as e:
        logging.error(f"Error reading default config file: {e}")
        return "Error reading default configuration file", 500

    # Helper functions for type conversion based on form input
    def to_bool(value):
        return value.lower() in ['true', '1', 't', 'y', 'yes']

    def to_int(value):
        try:
            return int(value)
        except ValueError:
            return value

    # Update the configuration with the data from the form
    for key, value in form_data.items():
        if key in config['Search Variables']:
            expected_type = type(config['Search Variables'][key])
            if expected_type is bool:
                config['Search Variables'][key] = to_bool(value)
            elif expected_type is int:
                config['Search Variables'][key] = to_int(value)
            else:
                config['Search Variables'][key] = value
        elif key in config['Logic Variables']['Good Data']:
            config['Logic Variables']['Good Data'][key] = to_int(value)
        elif key in config['Logic Variables']['Possibly Good Data']:
            config['Logic Variables']['Possibly Good Data'][key] = to_int(value)
        elif key == 'output_file_format':
            config['General']['output_file_format'] = 'xlsx' if value == 'excel' else 'csv'
        elif key == 'output_file_name':
            config['General']['output_file_name'] = value
        elif key in config['General']:
            config['General'][key] = value

    # Save the updated configuration to the unique file in the temp directory
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        logging.info(f"Config updated and saved as: {config_path}")
    except IOError as e:
        logging.error(f"Error writing to config file: {e}")
        return "Error writing to configuration file", 500

    # Store the path of the new config file in the app config for later use
    current_app.config['CURRENT_CONFIG_PATH'] = config_path

    return redirect(url_for('main.run_cleaning'))

@bp.route('/run_cleaning', methods=['POST'])
def run_cleaning():
    # Fetch the path of the newly generated configuration file
    config_path = current_app.config.get('CURRENT_CONFIG_PATH', os.path.join(current_app.root_path, 'config.json'))

    # Load the current configuration from the dynamically specified path
    with open(config_path, 'r') as f:
        config = json.load(f)

    # Redirect to the loading page immediately
    response = redirect(url_for('main.loading'))

    # Define the background task for fetching and cleaning data
    def background_task(app_context, config):
        with app_context:
            from .services.airbnb_apify import fetch_airbnb_data
            airbnb_data = fetch_airbnb_data(config)
            if not airbnb_data:
                logging.error("Failed to fetch data from Airbnb API.")
                return

            output_file_name = secure_filename(config['General']['output_file_name'])
            output_file_format = config['General']['output_file_format']
            temp_dir = current_app.config['TEMP_DIR']
            output_file_path = os.path.join(temp_dir, f"{output_file_name}.{output_file_format}")

            # Update the application configuration with the output file name and format
            current_app.config['output_file_name'] = output_file_name
            current_app.config['output_file_format'] = output_file_format

            # Directly call run_cleaning_process since it's defined in this file
            run_cleaning_process(config, airbnb_data, output_file_path, output_file_format)

            # Update the application configuration with the output file path and mark processing as complete
            current_app.config['output_file_path'] = output_file_path
            current_app.config['processing_complete'] = True

    # Execute the background task in a new thread
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
            
            # Attempt to save the data
            save_data(cleaned_df, output_file_path, output_file_format)
            logging.info(f"File successfully saved: {output_file_path}")
            
            # If everything went well up to this point, set the flags
            current_app.config['output_file_path'] = output_file_path
            current_app.config['processing_complete'] = True

        except Exception as e:
            logging.error(f"Error during data cleaning process: {e}", exc_info=True)
            # Ensure to reset the flag in case of an error
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
    if current_app.config.get('processing_complete', False):
        print("Processing complete.")  # Debugging
        return '', 200  # Indicate success
    else:
        print("Processing not complete.")  # Debugging
        return '', 204  # Indicate processing is still ongoing



@bp.route('/download')
def download():
    output_file_name = current_app.config.get('output_file_name')
    output_file_format = current_app.config.get('output_file_format')
    print(f"Output File Name: {output_file_name}")  # Debugging
    print(f"Output File Format: {output_file_format}")  # Debugging

    if output_file_name and output_file_format:
        filename = f"{output_file_name}.{output_file_format}"
        file_path = os.path.join(current_app.config['TEMP_DIR'], filename)
        print(f"Filename: {filename}")  # Debugging
        print(f"File Path: {file_path}")  # Debugging
        print(f"File exists: {os.path.exists(file_path)}")  # Debugging

        if os.path.exists(file_path):
            # Only pass the filename since that's what the template uses
            return render_template('download.html', file_name=filename)
        else:
            flash("File not found.")
    else:
        flash("No file information available.")

    return redirect(url_for('main.index'))



@bp.route('/download_file/<file_name>')
def download_file(file_name):
    """
    Send the file to the user upon request.
    """
    if os.path.exists(os.path.join(current_app.config['TEMP_DIR'], file_name)):
        return send_from_directory(directory=current_app.config['TEMP_DIR'], path=file_name, as_attachment=True)
    else:
        flash("File not found.")
        return redirect(url_for('main.index'))

