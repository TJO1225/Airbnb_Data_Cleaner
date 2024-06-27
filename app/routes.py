from flask import Blueprint, render_template, request, redirect, url_for, send_from_directory, flash, current_app, session
from app.services.data_cleaning import clean_airbnb_data, save_data
from app.services.airbnb_apify import fetch_airbnb_data
import os
import logging
from werkzeug.utils import secure_filename

logging.basicConfig(level=logging.INFO)

# Create a blueprint
bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """
    Display the main page with the form for user input.
    """
    return render_template('index.html')

@bp.route('/update_config', methods=['POST'])
def update_config():
    form_data = request.form.to_dict(flat=False)
    
    # Convert form data to proper nested dictionary structure
    config = {}
    for key, value in form_data.items():
        parts = key.split('[')
        d = config
        for part in parts[:-1]:
            part = part.rstrip(']')
            if part not in d:
                d[part] = {}
            d = d[part]
        d[parts[-1].rstrip(']')] = value[0]

    session['config_data'] = config
    return redirect(url_for('main.run_cleaning'))

@bp.route('/run_cleaning', methods=['GET', 'POST'])
def run_cleaning():
    config = session.get('config_data')
    if not config:
        flash("Configuration data is missing.")
        return redirect(url_for('main.index'))

    try:
        airbnb_data = fetch_airbnb_data(config)
        if not airbnb_data:
            logging.error("No data fetched from Airbnb API.")
            flash("No data fetched from Airbnb API.")
            return redirect(url_for('main.index'))

        output_file_name = secure_filename(config['General'].get('output_file_name', 'default_output'))
        output_file_format = config['General'].get('output_file_format', 'xlsx')
        output_file_path = os.path.join(current_app.config['TEMP_DIR'], f"{output_file_name}.{output_file_format}")

        cleaned_df = clean_airbnb_data(airbnb_data, config)
        save_data(cleaned_df, output_file_path, output_file_format)

        session['output_file_path'] = output_file_path
        session['output_file_name'] = output_file_name
        session['output_file_format'] = output_file_format
        session['processing_complete'] = True
        logging.info(f"Data processing completed and saved to {output_file_path}")

        return redirect(url_for('main.download'))
    except Exception as e:
        logging.error(f"Error during data processing: {e}", exc_info=True)
        flash(f"Error during data processing: {e}")
        session['processing_complete'] = False
        return redirect(url_for('main.index'))

@bp.route('/loading')
def loading():
    """
    Display the loading page while the data cleaning process runs.
    """
    if session.get('processing_complete', False):
        return redirect(url_for('main.download'))
    return render_template('loading.html')

@bp.route('/check_processing', methods=['GET'])
def check_processing():
    if session.get('processing_complete', False):
        print("Processing complete.")  # Debugging
        return '', 200  # Indicate success
    else:
        print("Processing not complete.")  # Debugging
        return '', 204  # Indicate processing is still ongoing

@bp.route('/download')
def download():
    output_file_name = session.get('output_file_name')
    output_file_format = session.get('output_file_format')

    if output_file_name and output_file_format:
        filename = f"{output_file_name}.{output_file_format}"
        file_path = os.path.join(current_app.config['TEMP_DIR'], filename)
        if os.path.exists(file_path):
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
