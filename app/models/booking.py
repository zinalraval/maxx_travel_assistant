from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base
import datetime

Base = declarative_base()

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    origin = Column(String)
    destination = Column(String)
    departure_date = Column(String)
    flight_number = Column(String)
    amount_paid = Column(Float)
    payment_status = Column(String, default="paid")
    booked_at = Column(DateTime, default=datetime.datetime.utcnow)
