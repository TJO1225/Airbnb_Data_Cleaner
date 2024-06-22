from sqlalchemy import Column, Integer, String, DateTime
from app import db


class AirbnbReview(db.Model):
    __tablename__ = "airbnb_reviews"
    id = Column(Integer, primary_key=True)
    listing_name = Column(String(100))
    review_date = Column(DateTime)
    review_text = Column(String(500))
    user_name = Column(String(50))
    rating = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<AirbnbReview {self.listing_name} {self.review_date}>"
