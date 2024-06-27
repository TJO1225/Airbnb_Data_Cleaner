import services.airbnb_apify as airbnb_apify
from services.data_cleaning import main as data_cleaning_main
from services.utils import load_config
import logging


logging.basicConfig(level=logging.INFO)


def main(config_path="config.json"):
    try:
        config = load_config(config_path)  # Load the dynamically specified config file
        airbnb_data = airbnb_apify.main(config)  # Pass the config to the airbnb_apify module
        data_cleaning_main(airbnb_data)  # Proceed with data cleaning
    except Exception as e:
        logging.error(f"Error in pipeline execution: {e}")

if __name__ == "__main__":
    # Get the configuration file path from command line arguments, defaulting to 'config.json'
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.json"
    main(config_path)

