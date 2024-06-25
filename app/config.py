import os

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "postgresql://sqlAdmin:Airbnbdata1@sqldb-asdk4-strag4-w8qh.database.windows.net:1433/sqldb-tenant-asdk4-strag4-w8qh"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = True
    TEMP_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'temp')
