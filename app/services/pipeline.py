import data_cleaning_packs.airbnb_apify as airbnb_apify
from data_cleaning_packs.data_cleaning import main as data_cleaning_main
from data_cleaning_packs.utils import load_config
import logging


logging.basicConfig(level=logging.INFO)


def main():
    try:
        config = load_config("config.json")
        airbnb_data = airbnb_apify.main()
        data_cleaning_main(airbnb_data)
    except Exception as e:
        logging.error(f"Error: {e}")


if __name__ == "__main__":
    main()
