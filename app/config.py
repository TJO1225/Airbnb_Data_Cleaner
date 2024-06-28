import os

class Config:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TEMP_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'temp')
    SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key')
    DEBUG = os.getenv('FLASK_DEBUG', 'False') == 'True'
    SESSION_TYPE = 'sqlalchemy'  # Use SQLAlchemy for session management
    SESSION_SQLALCHEMY = None  # This will be set in the app factory

class DevelopmentConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.getenv('AZURE_POSTGRESQL_CONNECTIONSTRING')
    DEBUG = True

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.getenv('AZURE_POSTGRESQL_CONNECTIONSTRING')
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
}
