from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_session import Session  # Import Flask-Session
import configparser
import os
import logging

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    
    # Load configuration from config.ini
    config = configparser.ConfigParser()
    config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))
    
    app.config['DEBUG'] = config.getboolean('DEFAULT', 'DEBUG')
    app.config['SECRET_KEY'] = config.get('DEFAULT', 'SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = config.get('DEFAULT', 'SQLALCHEMY_DATABASE_URI')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config.getboolean('DEFAULT', 'SQLALCHEMY_TRACK_MODIFICATIONS')
    
    # Configure session to use filesystem (instead of signed cookies)
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_PERMANENT'] = False
    
    # Ensure the temporary directory exists
    app.config['TEMP_DIR'] = os.path.join(app.root_path, 'temp')
    os.makedirs(app.config['TEMP_DIR'], exist_ok=True)
    
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Initialize the session
    Session(app)

    # Import parts of our application
    with app.app_context():
        from . import routes
        from .models import AirbnbReview
        db.create_all()

    # Register blueprint for handling routes
    from .routes import bp as main_bp
    app.register_blueprint(main_bp, url_prefix='/')

    logging.info("App created and blueprint registered.")

    return app
