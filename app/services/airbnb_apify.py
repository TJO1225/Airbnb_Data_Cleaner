import os
from apify_client import ApifyClient
from dotenv import load_dotenv
import logging

load_dotenv()

def fetch_airbnb_data(config):
    apify_token = os.getenv("APIFY_TOKEN")
    client = ApifyClient(apify_token)

    run_input = {
        "locationQuery": config["Search Variables"]["location_query"],
        "maxListings": int(config["Search Variables"]["max_listings"]),
        "startUrls": [],
        "includeReviews": config["Search Variables"]["include_reviews"],
        "maxReviews": int(config["Search Variables"]["max_reviews"]),
        "calendarMonths": int(config["Search Variables"]["calendar_months"]),
        "addMoreHostInfo": config["Search Variables"]["add_more_host_info"],
        "currency": config["Search Variables"]["currency"],
        "checkIn": config["Search Variables"]["check_in"],
        "checkOut": config["Search Variables"]["check_out"],
        "limitPoints": int(config["Search Variables"]["limit_points"]),
    }

    run = client.actor("GsNzxEKzE2vQ5d9HN").call(run_input=run_input)
    data = [item for item in client.dataset(run["defaultDatasetId"]).iterate_items()]
    logging.info(f"Fetched data: {data}")
    return data
