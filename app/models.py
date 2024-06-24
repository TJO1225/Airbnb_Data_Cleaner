from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Text
from app import db

class AirbnbReview(db.Model):
    __tablename__ = "airbnb_reviews"
    id = Column(Integer, primary_key=True)
    listing_name = Column(String(100))
    review_date = Column(DateTime)
    review_text = Column(Text)
    user_name = Column(String(50))
    rating = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    total_reviews = Column(Integer)
    total_months = Column(Integer)
    missing_months = Column(Integer)
    avg_reviews_per_month = Column(Float)
    high_season_reviews = Column(Integer)
    high_season = Column(Integer)
    high_season_insights = Column(String(100))
    bedroom_label = Column(String(50))
    number_of_guests = Column(Integer)
    url = Column(String(200))
    location = Column(String(100))
    stars = Column(Float)
    # Add any additional fields here as needed

    def __repr__(self):
        return f"<AirbnbReview {self.listing_name} {self.review_date}>"

class AirbnbRawData(db.Model):
    __tablename__ = "airbnb_raw_data"
    id = Column(Integer, primary_key=True)
    data = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<AirbnbRawData {self.id} {self.created_at}>"
