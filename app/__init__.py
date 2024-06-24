from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import configparser
import os
import logging

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    
    config = configparser.ConfigParser()
    config.read("app/config.ini")
    
    app.config['DEBUG'] = config.getboolean('DEFAULT', 'DEBUG')
    app.config['SECRET_KEY'] = config.get('DEFAULT', 'SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = config.get('DEFAULT', 'SQLALCHEMY_DATABASE_URI')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config.getboolean('DEFAULT', 'SQLALCHEMY_TRACK_MODIFICATIONS')

    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        from . import routes
        from .models import AirbnbReview
        db.create_all()

    # Register blueprint
    from .routes import bp as main_bp
    app.register_blueprint(main_bp, url_prefix='/')

    logging.info("App created and blueprint registered.")

    return app
