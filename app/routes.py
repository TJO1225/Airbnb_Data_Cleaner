from flask import Blueprint, render_template, request, redirect, url_for, send_from_directory, flash, current_app, session
from app.services.data_cleaning import clean_airbnb_data, save_data
from app.services.airbnb_apify import fetch_airbnb_data
import os
import logging
from werkzeug.utils import secure_filename
import threading

logging.basicConfig(level=logging.INFO)

# Create a blueprint
bp = Blueprint('main', __name__)

# Global variable to store processing status
processing_status = {
    'complete': False,
    'output_file_path': '',
    'output_file_name': '',
    'output_file_format': ''
}

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
    config = {
        "Search Variables": {
            "location_query": form_data.get("location_query", [""])[0],
            "max_listings": int(form_data.get("max_listings", [0])[0]),
            "include_reviews": form_data.get("include_reviews", ["false"])[0].lower() == 'true',
            "max_reviews": int(form_data.get("max_reviews", [0])[0]),
            "calendar_months": int(form_data.get("calendar_months", [0])[0]),
            "add_more_host_info": form_data.get("add_more_host_info", ["false"])[0].lower() == 'true',
            "currency": form_data.get("currency", [""])[0],
            "check_in": form_data.get("check_in", [""])[0],
            "check_out": form_data.get("check_out", [""])[0],
            "limit_points": int(form_data.get("limit_points", [0])[0])
        },
        "Logic Variables": {
            "Good Data": {
                "total_months": int(form_data.get("total_months", [0])[0]),
                "missing_months": int(form_data.get("missing_months", [0])[0]),
                "avg_reviews_per_month": int(form_data.get("avg_reviews_per_month", [0])[0]),
                "min_reviews": int(form_data.get("min_reviews", [0])[0]),
                "high_season_reviews": int(form_data.get("high_season_reviews", [0])[0])
            },
            "Possibly Good Data": {
                "total_months": int(form_data.get("total_months_pgd", [0])[0]),
                "missing_months": int(form_data.get("missing_months_pgd", [0])[0]),
                "avg_reviews_per_month": int(form_data.get("avg_reviews_per_month_pgd", [0])[0]),
                "min_reviews": int(form_data.get("min_reviews_pgd", [0])[0]),
                "high_season_reviews": int(form_data.get("high_season_reviews_pgd", [0])[0])
            }
        },
        "General": {
            "output_file_name": form_data.get("output_file_name", [""])[0],
            "output_file_format": form_data.get("output_file_format", [""])[0],
            "high_season_override": form_data.get("high_season_override", [""])[0],
            "min_bedrooms": int(form_data.get("min_bedrooms", [0])[0])
        }
    }

    session['config_data'] = config
    processing_status['complete'] = False

    return redirect(url_for('main.run_cleaning'))

def background_task(app, config):
    with app.app_context():
        try:
            airbnb_data = fetch_airbnb_data(config)
            if not airbnb_data:
                logging.error("No data fetched from Airbnb API.")
                return

            output_file_name = secure_filename(config['General'].get('output_file_name', 'default_output'))
            output_file_format = config['General'].get('output_file_format', 'xlsx')
            output_file_path = os.path.join(app.config['TEMP_DIR'], f"{output_file_name}.{output_file_format}")

            cleaned_df = clean_airbnb_data(airbnb_data, config)
            save_data(cleaned_df, output_file_path, output_file_format)

            processing_status['output_file_path'] = output_file_path
            processing_status['output_file_name'] = output_file_name
            processing_status['output_file_format'] = output_file_format
            processing_status['complete'] = True
            logging.info(f"Data processing completed and saved to {output_file_path}")
        except Exception as e:
            logging.error(f"Error during data processing: {e}", exc_info=True)
            processing_status['complete'] = False

@bp.route('/run_cleaning', methods=['GET', 'POST'])
def run_cleaning():
    config = session.get('config_data')
    if not config:
        flash("Configuration data is missing.")
        return redirect(url_for('main.index'))

    app = current_app._get_current_object()
    threading.Thread(target=background_task, args=(app, config)).start()
    return redirect(url_for('main.loading'))

@bp.route('/loading')
def loading():
    """
    Display the loading page while the data cleaning process runs.
    """
    return render_template('loading.html')

@bp.route('/check_processing', methods=['GET'])
def check_processing():
    if processing_status['complete']:
        return '', 200  # Indicate success
    else:
        return '', 204  # Indicate processing is still ongoing

@bp.route('/download')
def download():
    output_file_name = processing_status['output_file_name']
    output_file_format = processing_status['output_file_format']

    if output_file_name and output_file_format:
        filename = f"{output_file_name}.{output_file_format}"
        file_path = processing_status['output_file_path']
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
    file_path = processing_status['output_file_path']
    if os.path.exists(file_path):
        return send_from_directory(directory=current_app.config['TEMP_DIR'], path=file_name, as_attachment=True)
    else:
        flash("File not found.")
        return redirect(url_for('main.index'))
