from flask import Flask, render_template, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_session import Session
import os
import logging

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# Load configuration based on environment
if "WEBSITE_HOSTNAME" in os.environ:
    # Running on Azure
    app.config.from_object('config.ProductionConfig')
else:
    # Local development
    app.config.from_object('config.DevelopmentConfig')

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Set SQLAlchemy object for Flask-Session
app.config['SESSION_SQLALCHEMY'] = db

# Initialize Flask-Session
session = Session(app)

# Import your blueprint
from app.routes import bp as main_bp

# Register the blueprint
app.register_blueprint(main_bp)

@app.route("/", methods=["GET"])
def index():
    logging.info("Request for index page received")
    return render_template("index.html")

@app.route("/run_cleaning", methods=["POST"])
def run_cleaning():
    try:
        # Your data processing logic here
        flash("Data processing completed successfully!")
    except Exception as e:
        logging.error(f"Error during data processing: {e}")
        flash("An error occurred during data processing.")
    return redirect(url_for('index'))

@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon"
    )

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
