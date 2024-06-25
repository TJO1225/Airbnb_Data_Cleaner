import json
import pandas as pd
from datetime import datetime
from collections import defaultdict
import logging
import os
import re
from .utils import load_config
from app.models import AirbnbRawData, AirbnbReview
from app import db

logging.basicConfig(level=logging.INFO)


def load_config(config_path):
    with open(config_path, "r") as file:
        config = json.load(file)
    return config


def calculate_high_season(reviews, high_season_override):
    review_dates = [
        datetime.strptime(review["createdAt"], "%Y-%m-%dT%H:%M:%S.%fZ").date()
        for review in reviews
    ]
    review_counts = defaultdict(int)

    for date in review_dates:
        quarter = (date.month - 1) // 3 + 1
        review_counts[quarter] += 1

    high_season = max(review_counts, key=review_counts.get, default=None)
    if high_season_override:
        high_season = int(high_season_override[-1])
    high_season_reviews = review_counts.get(high_season, 0) if high_season else 0

    return high_season, high_season_reviews


def get_thresholds(config):
    return {
        "good_data": config["Logic Variables"].get("Good Data", {}),
        "possibly_good_data": config["Logic Variables"].get("Possibly Good Data", {}),
        "high_season_override": config["General"].get("high_season_override", ""),
    }


class AirbnbDataCleaner:
    def __init__(self, airbnb_data):
        self.airbnb_data = airbnb_data
        self.cleaned_data = defaultdict(list)
        self.high_season = None
        self.high_season_reviews = 0

    def load_data(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                self.raw_data = json.load(f)
        except FileNotFoundError:
            logging.error(f"File not found: {file_path}")
        except json.JSONDecodeError:
            logging.error(f"Invalid JSON format in file: {file_path}")

    def get_reviews(self, listing):
        return listing.get("reviews", [])

    def get_bedroom_count(self, listing):
        bedroom_label = listing.get("bedroomLabel", "0")
        match = re.search(r"(\d+)", bedroom_label)
        if match:
            return int(match.group(1))
        return 0

    def get_historical_data(self, reviews):
        review_months = defaultdict(int)
        earliest_review = None
        latest_review = None

        for review in reviews:
            review_date = datetime.strptime(
                review["createdAt"], "%Y-%m-%dT%H:%M:%S.%fZ"
            ).date()

            if earliest_review is None or review_date < earliest_review:
                earliest_review = review_date
            if latest_review is None or review_date > latest_review:
                latest_review = review_date

            review_month = review_date.strftime("%Y-%m")
            review_months[review_month] += 1

        if earliest_review and latest_review:
            total_months = (latest_review.year - earliest_review.year) * 12 + (
                latest_review.month - earliest_review.month + 1
            )
        else:
            total_months = 0

        missing_months = 12 - len(review_months) if total_months <= 12 else 0

        avg_reviews_per_month = (
            sum(review_months.values()) / total_months if total_months > 0 else 0
        )

        return {
            "total_months": total_months,
            "missing_months": missing_months,
            "avg_reviews_per_month": round(avg_reviews_per_month, 2),
            "total_reviews": len(reviews),
        }

    def clean_data(self, thresholds):
        all_reviews = [
            review
            for listing in self.airbnb_data
            for review in self.get_reviews(listing)
        ]
        self.high_season, self.high_season_reviews = calculate_high_season(
            all_reviews, thresholds["high_season_override"]
        )

        for idx, listing in enumerate(self.airbnb_data, start=1):
            reviews = self.get_reviews(listing)
            historical_data = self.get_historical_data(reviews)
            if self.high_season:
                historical_data["high_season_reviews"] = sum(
                    1
                    for review in reviews
                    if (
                        datetime.strptime(review["createdAt"], "%Y-%m-%dT%H:%M:%S.%fZ")
                        .date()
                        .month
                        - 1
                    )
                    // 3
                    + 1
                    == self.high_season
                )
            else:
                historical_data["high_season_reviews"] = 0
            historical_data["high_season"] = self.high_season
            category, reason = self.categorize_listing(
                listing, historical_data, thresholds
            )
            listing_with_data = listing.copy()
            listing_with_data.update(historical_data)
            listing_with_data["Quality Rating Reason"] = reason
            listing_with_data["High Season Insights"] = (
                f"{historical_data['high_season_reviews']} Reviews in Q{self.high_season}"
                if self.high_season
                else "No high season"
            )
            self.cleaned_data[category].append(listing_with_data)
            logging.info(f"Listing {idx}: {category} ({historical_data})")
        return self.cleaned_data

    def categorize_listing(self, listing, historical_data, thresholds):
        good_data_thresholds = thresholds.get("good_data", {})
        possibly_good_data_thresholds = thresholds.get("possibly_good_data", {})

        if self.is_good_data(listing, historical_data, good_data_thresholds):
            return "Good Data", "Good data"

        if self.is_possibly_good_data(
            listing, historical_data, possibly_good_data_thresholds
        ):
            return "Possibly Good Data", self.not_good_data_reason(
                listing, historical_data, possibly_good_data_thresholds
            )

        reason = self.not_good_data_reason(
            listing, historical_data, good_data_thresholds
        )
        return "Not Good Data", reason

    def is_good_data(self, listing, historical_data, thresholds):
        return (
            historical_data["total_months"]
            >= thresholds.get("total_months", float("inf"))
            and historical_data["missing_months"]
            <= thresholds.get("missing_months", float("-inf"))
            and historical_data["avg_reviews_per_month"]
            >= thresholds.get("avg_reviews_per_month", float("-inf"))
            and historical_data["total_reviews"]
            >= thresholds.get("min_reviews", float("inf"))
            and self.get_bedroom_count(listing)
            >= thresholds.get("min_bedrooms", float("inf"))
            and historical_data["high_season_reviews"]
            >= thresholds.get("high_season_reviews", float("-inf"))
        )

    def is_possibly_good_data(self, listing, historical_data, thresholds):
        return (
            thresholds.get("total_months", float("inf"))
            > historical_data["total_months"]
            >= thresholds.get("total_months", float("-inf"))
            and historical_data["missing_months"]
            <= thresholds.get("missing_months", float("-inf"))
            and historical_data["avg_reviews_per_month"]
            >= thresholds.get("avg_reviews_per_month", float("-inf"))
            and historical_data["total_reviews"]
            >= thresholds.get("min_reviews", float("inf"))
            and self.get_bedroom_count(listing)
            >= thresholds.get("min_bedrooms", float("inf"))
            and historical_data["high_season_reviews"]
            >= thresholds.get("high_season_reviews", float("-inf"))
        )

    def not_good_data_reason(self, listing, historical_data, thresholds):
        reasons = []
        if historical_data["total_reviews"] < thresholds.get(
            "min_reviews", float("inf")
        ):
            reasons.append(f"Less than {thresholds.get('min_reviews')} total reviews")
        if historical_data["total_months"] < thresholds.get(
            "total_months", float("inf")
        ):
            reasons.append(
                f"Only {historical_data['total_months']} months of historical data"
            )
        if historical_data["missing_months"] > thresholds.get(
            "missing_months", float("-inf")
        ):
            reasons.append(
                f"More than {thresholds.get('missing_months')} missing months of data"
            )
        if historical_data["avg_reviews_per_month"] < thresholds.get(
            "avg_reviews_per_month", float("-inf")
        ):
            reasons.append(
                f"Less than {thresholds.get('avg_reviews_per_month')} reviews per month on average"
            )
        if self.get_bedroom_count(listing) < thresholds.get(
            "min_bedrooms", float("inf")
        ):
            reasons.append(f"Only {self.get_bedroom_count(listing)} bedrooms")
        if historical_data["high_season_reviews"] < thresholds.get(
            "high_season_reviews", float("-inf")
        ):
            reasons.append(
                f"Less than {thresholds.get('high_season_reviews')} reviews in high season"
            )
        return "; ".join(reasons)

    def create_dataframe(self, cleaned_data):
        columns_order = [
            "Listing Name",
            "Data Quality Category",
            "Quality Rating Reason",
            "total_reviews",
            "total_months",
            "missing_months",
            "avg_reviews_per_month",
            "high_season_reviews",
            "high_season",
            "High Season Insights",
            "bedroomLabel",
            "numberOfGuests",
            "url",
            "name",
            "Location",
            "stars",
        ]

        data = []
        for category, listings in cleaned_data.items():
            for listing in listings:
                row = {
                    "Listing Name": listing["name"],
                    "Data Quality Category": category,
                    "Quality Rating Reason": listing["Quality Rating Reason"],
                    "total_reviews": listing["total_reviews"],
                    "total_months": listing["total_months"],
                    "missing_months": listing["missing_months"],
                    "avg_reviews_per_month": listing["avg_reviews_per_month"],
                    "high_season_reviews": listing["high_season_reviews"],
                    "high_season": listing["high_season"],
                    "High Season Insights": listing["High Season Insights"],
                    "bedroomLabel": listing.get("bedroomLabel", ""),
                    "numberOfGuests": listing.get("numberOfGuests", ""),
                    "url": listing.get("url", ""),
                    "name": listing.get("name", ""),
                    "Location": listing.get("Location", ""),
                    "stars": listing.get("stars", 0),
                }
                additional_columns = {k: v for k, v in listing.items() if k not in row}
                row.update(additional_columns)
                data.append(row)

        df = pd.DataFrame(data)
        df = df[columns_order + [col for col in df.columns if col not in columns_order]]
        df = df.sort_values(
            by="Data Quality Category",
            ascending=False,
            key=lambda col: col.map(
                {"Good Data": 2, "Possibly Good Data": 1, "Not Good Data": 0}
            ),
        )
        return df

    def save_dataframe(self, df, file_path, file_format="csv"):
        if file_format == "csv":
            df.to_csv(file_path, index=False)
        elif file_format == "excel":
            df.to_excel(file_path, index=False)
        else:
            logging.error(f"Unsupported file format: {file_format}")


def clean_airbnb_data(raw_data_entries, config):
    """
    Clean the raw Airbnb data based on the provided configuration.
    """
    logging.info("Starting to clean Airbnb data.")
    
    # Check if raw_data_entries is a list of dictionaries
    if isinstance(raw_data_entries, list) and all(isinstance(entry, dict) for entry in raw_data_entries):
        all_data = raw_data_entries  # No need to access `.data`
    else:
        logging.error("Invalid data format received for cleaning.")
        raise ValueError("Invalid data format received for cleaning.")

    data_cleaner = AirbnbDataCleaner(all_data)
    thresholds = get_thresholds(config)
    cleaned_data = data_cleaner.clean_data(thresholds)
    df = data_cleaner.create_dataframe(cleaned_data)
    
    logging.info("Airbnb data cleaned successfully.")
    return df



def save_data(df, config):
    """
    Save cleaned data to the database and generate output file.
    """
    # Serialize cleaned data to JSON
    serialized_data = df.to_json(orient='records')

    # Save cleaned data back to the database
    raw_data_entry = AirbnbRawData(data=serialized_data)
    db.session.add(raw_data_entry)
    db.session.commit()

    # Save cleaned data back to the database
    for index, row in df.iterrows():
        review = AirbnbReview(
            listing_name=row.get('Listing Name', None),
            review_date=row.get('review_date', None),
            review_text=row.get('review_text', None),
            user_name=row.get('user_name', None),
            rating=row.get('rating', None),
            created_at=row.get('created_at', None)
        )
        db.session.add(review)
    db.session.commit()
    
    # Generate output file for download
    output_file_name = config["General"]["output_file_name"]
    output_file_format = config["General"]["output_file_format"]
    output_file_path = os.path.join("outputs", f"{output_file_name}.{output_file_format}")

    if output_file_format == "csv":
        df.to_csv(output_file_path, index=False)
    elif output_file_format == "excel":
        df.to_excel(output_file_path, index=False)
    else:
        logging.error("Unsupported file format")

    return output_file_path

def main(airbnb_data):
    try:
        config = load_config("config.json")
        cleaned_df = clean_airbnb_data(airbnb_data, config)
        save_data(cleaned_df, config)
    except Exception as e:
        logging.error(f"Error: {e}")


if __name__ == "__main__":
    # This script expects the airbnb_data to be passed as an argument
    # We'll use the updated airbnb_apify.py script to pass the data
    pass
