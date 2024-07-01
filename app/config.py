import os
from configparser import ConfigParser

config = ConfigParser()
config.read('config.ini')

class Config:
    SQLALCHEMY_TRACK_MODIFICATIONS = config['DEFAULT'].getboolean('SQLALCHEMY_TRACK_MODIFICATIONS')
    TEMP_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'temp')
    SECRET_KEY = config['DEFAULT']['SECRET_KEY']
    DEBUG = config['DEFAULT'].getboolean('DEBUG')

class DevelopmentConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', config['DEFAULT']['SQLALCHEMY_DATABASE_URI'])
    DEBUG = True

class ProductionConfig(Config):
    # Here we prioritize the environment variable `AZURE_MSSQL_CONNECTIONSTRING`
    # and fall back to the `SQLALCHEMY_DATABASE_URI` from the config file
    SQLALCHEMY_DATABASE_URI = os.getenv('AZURE_MSSQL_CONNECTIONSTRING', config['DEFAULT']['SQLALCHEMY_DATABASE_URI'])
    DEBUG = False

config_dict = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
}
