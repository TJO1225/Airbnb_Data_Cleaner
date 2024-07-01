# test_db_connection.py
from sqlalchemy import create_engine

DATABASE_URI = 'mssql+pyodbc://sqlAdmin:Stragent1@sqldb-asdk4-strag4-w8qh.database.windows.net:1433/sqldb-tenant-asdk4-strag4-w8qh?driver=ODBC+Driver+17+for+SQL+Server'

try:
    engine = create_engine(DATABASE_URI)
    connection = engine.connect()
    print("Connection successful!")
    connection.close()
except Exception as e:
    print(f"Connection failed: {e}")
