import os
from sqlalchemy import create_engine

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Get the database URL from the environment variables
database_url = os.getenv('AZURE_POSTGRESQL_CONNECTIONSTRING')

print(f"Connecting to database using: {database_url}")

try:
    # Create an engine and connect to the database
    engine = create_engine(database_url)
    with engine.connect() as connection:
        result = connection.execute("SELECT 1")
        print("Connection successful:", result.fetchone())
except Exception as e:
    print("Error connecting to the database:", e)
