import os
import json
from apify_client import ApifyClient
from dotenv import load_dotenv
from services.utils import load_config

load_dotenv()


def load_config(file_path):
    with open(file_path, "r") as f:
        return json.load(f)


def fetch_airbnb_data(config):
    # Initialize the ApifyClient with your API token
    apify_token = os.getenv("APIFY_TOKEN")
    client = ApifyClient(apify_token)

    # Prepare the Actor input
    run_input = {
        "locationQuery": config["Search Variables"]["location_query"],
        "maxListings": config["Search Variables"]["max_listings"],
        "startUrls": [],
        "includeReviews": config["Search Variables"]["include_reviews"],
        "maxReviews": config["Search Variables"]["max_reviews"],
        "calendarMonths": config["Search Variables"]["calendar_months"],
        "addMoreHostInfo": config["Search Variables"]["add_more_host_info"],
        "currency": config["Search Variables"]["currency"],
        "checkIn": config["Search Variables"]["check_in"],
        "checkOut": config["Search Variables"]["check_out"],
        "limitPoints": config["Search Variables"]["limit_points"],
    }

    # Run the Actor and wait for it to finish
    run = client.actor("GsNzxEKzE2vQ5d9HN").call(run_input=run_input)

    # Fetch and return Actor results from the run's dataset (if there are any)
    data = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        data.append(item)
    return data


def main():
    config = load_config("config.json")
    airbnb_data = fetch_airbnb_data(config)
    return airbnb_data


if __name__ == "__main__":
    airbnb_data = main()
    print(airbnb_data)
