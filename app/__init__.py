from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
import configparser

db = SQLAlchemy()
migrate = Migrate()


def create_app():
    app = Flask(__name__)
    config = configparser.ConfigParser()
    config.read("app/config.ini")
    app.config.from_object("app.config.Config")

    db.init_app(app)
    migrate.init_app(app, db)

    logging.basicConfig(level=logging.INFO)

    with app.app_context():
        from . import routes, models

        db.create_all()

    return app
