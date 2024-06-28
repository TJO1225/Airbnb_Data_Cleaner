import os

class Config:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TEMP_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'temp')
    SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key')
    DEBUG = os.getenv('FLASK_DEBUG', 'False') == 'True'
    SESSION_TYPE = 'filesystem'  # Ensure sessions are stored on the filesystem

class DevelopmentConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql://sqlAdmin:Airbnbdata1@sqldb-asdk4-strag4-w8qh.database.windows.net:1433/sqldb-tenant-asdk4-strag4-w8qh')
    DEBUG = True

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
}
