import pandas as pd
from datetime import datetime
from collections import defaultdict
import logging
import os
import re
import json

logging.basicConfig(level=logging.INFO)

def calculate_high_season(reviews, high_season_override):
    review_dates = [datetime.strptime(review["createdAt"], "%Y-%m-%dT%H:%M:%S.%fZ").date() for review in reviews]
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
    thresholds = {
        "good_data": config["Logic Variables"].get("Good Data", {}),
        "possibly_good_data": config["Logic Variables"].get("Possibly Good Data", {}),
        "high_season_override": config["General"].get("high_season_override", ""),
        "min_bedrooms": config["General"].get("min_bedrooms", 0)
    }
    logging.info(f"Thresholds loaded: {thresholds}")
    return thresholds

class AirbnbDataCleaner:
    def __init__(self, airbnb_data):
        self.airbnb_data = airbnb_data
        self.cleaned_data = defaultdict(list)
        self.high_season = None
        self.high_season_reviews = 0

        # Add Bedrooms count to each listing during initialization
        for listing in self.airbnb_data:
            listing["Bedrooms"] = self.get_bedroom_count(listing)
            logging.info(f"Extracted Bedrooms for listing {listing.get('id')}: {listing['Bedrooms']}")

    def get_reviews(self, listing):
        return listing.get("reviews", [])

    def get_bedroom_count(self, listing):
        bedroom_label = listing.get("bedroomLabel", "0")
        if "studio" in bedroom_label.lower():
            return 0
        match = re.search(r"(\d+)", bedroom_label)
        if match:
            return int(match.group(1))  # Ensure the result is an integer
        return 0

    def get_historical_data(self, reviews):
        review_months = defaultdict(int)
        earliest_review = None
        latest_review = None

        for review in reviews:
            review_date = datetime.strptime(review["createdAt"], "%Y-%m-%dT%H:%M:%S.%fZ").date()

            if earliest_review is None or review_date < earliest_review:
                earliest_review = review_date
            if latest_review is None or review_date > latest_review:
                latest_review = review_date

            review_month = review_date.strftime("%Y-%m")
            review_months[review_month] += 1

        if earliest_review and latest_review:
            total_months = (latest_review.year - earliest_review.year) * 12 + (latest_review.month - earliest_review.month + 1)
        else:
            total_months = 0

        missing_months = 12 - len(review_months) if total_months <= 12 else 0

        avg_reviews_per_month = sum(review_months.values()) / total_months if total_months > 0 else 0

        return {
            "total_months": total_months,
            "missing_months": missing_months,
            "avg_reviews_per_month": round(avg_reviews_per_month, 2),
            "total_reviews": len(reviews),
            "high_season_reviews": 0  # Initialize high season reviews
        }

    def clean_data(self, thresholds):
        all_reviews = [
            review
            for listing in self.airbnb_data
            for review in self.get_reviews(listing)
        ]
        self.high_season, self.high_season_reviews = calculate_high_season(all_reviews, thresholds["high_season_override"])

        logging.info(f"Total listings to process: {len(self.airbnb_data)}")

        for idx, listing in enumerate(self.airbnb_data, start=1):
            try:
                logging.info(f"Processing listing {idx}/{len(self.airbnb_data)}: {listing.get('id')}")
                reviews = self.get_reviews(listing)
                historical_data = self.get_historical_data(reviews)
                if self.high_season:
                    historical_data["high_season_reviews"] = sum(
                        1
                        for review in reviews
                        if (datetime.strptime(review["createdAt"], "%Y-%m-%dT%H:%M:%S.%fZ").date().month - 1) // 3 + 1 == self.high_season
                    )
                historical_data["high_season"] = self.high_season
                listing_with_data = listing.copy()

                # Add logging for Bedrooms and min_bedrooms check
                logging.info(f"Listing {idx} Bedrooms: {listing_with_data['Bedrooms']}")

                # Check if Bedrooms meet the minimum requirement
                if listing_with_data["Bedrooms"] < thresholds["min_bedrooms"]:
                    category = "Not Good Data"
                    reason = f"Only {listing_with_data['Bedrooms']} bedrooms, requires at least {thresholds['min_bedrooms']} bedrooms"
                else:
                    category, reason = self.categorize_listing(listing_with_data, historical_data, thresholds)

                listing_with_data.update(historical_data)
                listing_with_data["Quality Rating Reason"] = reason
                listing_with_data["High Season Insights"] = (
                    f"{historical_data['high_season_reviews']} Reviews in Q{self.high_season}" if self.high_season else "No high season"
                )
                self.cleaned_data[category].append(listing_with_data)
                logging.info(f"Listing {idx}: {category} ({historical_data}) - Reason: {reason}")
            except Exception as e:
                logging.error(f"Error processing listing {idx}/{len(self.airbnb_data)}: {e}", exc_info=True)
        return self.cleaned_data

    def categorize_listing(self, listing, historical_data, thresholds):
        good_data_thresholds = thresholds.get("good_data", {})
        possibly_good_data_thresholds = thresholds.get("possibly_good_data", {})

        logging.info(f"Categorizing listing {listing.get('id')} with Bedrooms: {listing['Bedrooms']}")

        if self.is_good_data(listing, historical_data, good_data_thresholds):
            return "Good Data", "Good Data"

        if self.is_possibly_good_data(listing, historical_data, possibly_good_data_thresholds):
            return "Possibly Good Data", self.possibly_good_data_reason(listing, historical_data, good_data_thresholds, possibly_good_data_thresholds)

        reason = self.not_good_data_reason(listing, historical_data, good_data_thresholds, possibly_good_data_thresholds)
        return "Not Good Data", reason

    def is_good_data(self, listing, historical_data, thresholds):
        result = (
            historical_data["total_months"] >= thresholds.get("total_months", float("inf"))
            and historical_data["missing_months"] <= thresholds.get("missing_months", float("-inf"))
            and historical_data["avg_reviews_per_month"] >= thresholds.get("avg_reviews_per_month", float("-inf"))
            and historical_data["total_reviews"] >= thresholds.get("min_reviews", float("inf"))
            and listing["Bedrooms"] >= thresholds.get("min_bedrooms", 0)
            and historical_data["high_season_reviews"] >= thresholds.get("high_season_reviews", float("-inf"))
        )
        logging.info(f"Checking if listing {listing.get('id')} is good data: {result}")
        return result

    def is_possibly_good_data(self, listing, historical_data, thresholds):
        result = (
            historical_data["total_months"] >= thresholds.get("total_months", float("-inf"))
            and historical_data["missing_months"] <= thresholds.get("missing_months", float("-inf"))
            and historical_data["avg_reviews_per_month"] >= thresholds.get("avg_reviews_per_month", float("-inf"))
            and historical_data["total_reviews"] >= thresholds.get("min_reviews", float("inf"))
            and listing["Bedrooms"] >= thresholds.get("min_bedrooms", 0)
            and historical_data["high_season_reviews"] >= thresholds.get("high_season_reviews", float("-inf"))
        )
        logging.info(f"Checking if listing {listing.get('id')} is possibly good data: {result}")
        return result

    def possibly_good_data_reason(self, listing, historical_data, good_data_thresholds, possibly_good_data_thresholds):
        reasons = []
        for key in possibly_good_data_thresholds:
            if key in historical_data:
                good_value = good_data_thresholds.get(key)
                possibly_good_value = possibly_good_data_thresholds.get(key)
                actual_value = historical_data[key]
                if actual_value < good_value:
                    if actual_value >= possibly_good_value:
                        reasons.append(f"{key.replace('_', ' ').title()} is Possibly Good Data: {actual_value} (threshold: {possibly_good_value})")
                    else:
                        reasons.append(f"{key.replace('_', ' ').title()} is below Possibly Good Data threshold: {actual_value} (threshold: {possibly_good_value})")
        logging.info(f"Possibly Good Data Reason for listing {listing.get('id')}: {reasons}")
        return "; ".join(reasons)

    def not_good_data_reason(self, listing, historical_data, good_data_thresholds, possibly_good_data_thresholds):
        reasons = []
        for key in good_data_thresholds:
            if key in historical_data:
                good_value = good_data_thresholds.get(key)
                possibly_good_value = possibly_good_data_thresholds.get(key)
                actual_value = historical_data[key]
                if actual_value < possibly_good_value:
                    reasons.append(f"{key.replace('_', ' ').title()} is below Possibly Good Data threshold: {actual_value} (threshold: {possibly_good_value})")
                elif actual_value < good_value:
                    reasons.append(f"{key.replace('_', ' ').title()} is Possibly Good Data: {actual_value} (threshold: {possibly_good_value})")
                else:
                    reasons.append(f"{key.replace('_', ' ').title()} is Good Data: {actual_value}")
        logging.info(f"Not Good Data Reason for listing {listing.get('id')}: {reasons}")
        return "; ".join(reasons)

    def create_dataframe(self, cleaned_data):
        columns_order = [
            "Listing Name",
            "Data Quality Category",
            "Quality Rating Reason",
            "Bedrooms",
            "total_reviews",
            "total_months",
            "missing_months",
            "avg_reviews_per_month",
            "high_season_reviews",
            "high_season",
            "High Season Insights",
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
                    "Bedrooms": listing.get("Bedrooms", 0),
                    "total_reviews": listing["total_reviews"],
                    "total_months": listing["total_months"],
                    "missing_months": listing["missing_months"],
                    "avg_reviews_per_month": listing["avg_reviews_per_month"],
                    "high_season_reviews": listing["high_season_reviews"],
                    "high_season": listing["high_season"],
                    "High Season Insights": listing["High Season Insights"],
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
            key=lambda col: col.map({"Good Data": 2, "Possibly Good Data": 1, "Not Good Data": 0}),
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
    logging.info("Starting to clean Airbnb data.")
    if not isinstance(raw_data_entries, list) or not all(isinstance(entry, dict) for entry in raw_data_entries):
        logging.error("Invalid data format received for cleaning.")
        raise ValueError("Invalid data format received for cleaning.")
    data_cleaner = AirbnbDataCleaner(raw_data_entries)
    thresholds = get_thresholds(config)
    cleaned_data = data_cleaner.clean_data(thresholds)
    df = data_cleaner.create_dataframe(cleaned_data)
    logging.info("Airbnb data cleaned successfully.")
    return df

def save_data(df, output_file_path, output_file_format):
    logging.info(f"Saving data to: {output_file_path} with format: {output_file_format}")
    if output_file_format == "csv":
        df.to_csv(output_file_path, index=False)
    elif output_file_format == "xlsx":
        df.to_excel(output_file_path, index=False, engine='openpyxl')
    if os.path.exists(output_file_path):
        logging.info(f"File successfully saved: {output_file_path}")
    else:
        logging.error(f"File not found after save attempt: {output_file_path}")

def clean_airbnb_data(raw_data_entries, config):
    logging.info("Starting to clean Airbnb data.")
    if not isinstance(raw_data_entries, list) or not all(isinstance(entry, dict) for entry in raw_data_entries):
        logging.error("Invalid data format received for cleaning.")
        raise ValueError("Invalid data format received for cleaning.")
    data_cleaner = AirbnbDataCleaner(raw_data_entries)
    thresholds = get_thresholds(config)
    cleaned_data = data_cleaner.clean_data(thresholds)
    df = data_cleaner.create_dataframe(cleaned_data)
    logging.info("Airbnb data cleaned successfully.")
    return df

def save_data(df, output_file_path, output_file_format):
    logging.info(f"Saving data to: {output_file_path} with format: {output_file_format}")
    if output_file_format == "csv":
        df.to_csv(output_file_path, index=False)
    elif output_file_format == "xlsx":
        df.to_excel(output_file_path, index=False, engine='openpyxl')
    if os.path.exists(output_file_path):
        logging.info(f"File successfully saved: {output_file_path}")
    else:
        logging.error(f"File not found after save attempt: {output_file_path}")


def clean_airbnb_data(raw_data_entries, config):
    logging.info("Starting to clean Airbnb data.")
    if not isinstance(raw_data_entries, list) or not all(isinstance(entry, dict) for entry in raw_data_entries):
        logging.error("Invalid data format received for cleaning.")
        raise ValueError("Invalid data format received for cleaning.")
    data_cleaner = AirbnbDataCleaner(raw_data_entries)
    thresholds = get_thresholds(config)
    cleaned_data = data_cleaner.clean_data(thresholds)
    df = data_cleaner.create_dataframe(cleaned_data)
    logging.info("Airbnb data cleaned successfully.")
    return df

def save_data(df, output_file_path, output_file_format):
    logging.info(f"Saving data to: {output_file_path} with format: {output_file_format}")
    if output_file_format == "csv":
        df.to_csv(output_file_path, index=False)
    elif output_file_format == "xlsx":
        df.to_excel(output_file_path, index=False, engine='openpyxl')
    if os.path.exists(output_file_path):
        logging.info(f"File successfully saved: {output_file_path}")
    else:
        logging.error(f"File not found after save attempt: {output_file_path}")
