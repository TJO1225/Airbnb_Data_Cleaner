from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import configparser
import os

# Initialize SQLAlchemy and Migrate here, but do not associate them with the app yet.
db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    
    # Load configuration from config.ini file
    config = configparser.ConfigParser()
    config.read("app/config.ini")
    
    # Set configurations for the app
    app.config['DEBUG'] = config.getboolean('DEFAULT', 'DEBUG')
    app.config['SECRET_KEY'] = config.get('DEFAULT', 'SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = config.get('DEFAULT', 'SQLALCHEMY_DATABASE_URI')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config.getboolean('DEFAULT', 'SQLALCHEMY_TRACK_MODIFICATIONS')

    # Now, associate db and migrate with the app inside the factory function.
    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        # Import routes and models here to avoid circular imports
        from . import routes
        from .models import AirbnbReview
        # Create database tables for our data models
        db.create_all()

    return app