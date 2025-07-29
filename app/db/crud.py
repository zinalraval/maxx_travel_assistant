from app.models.booking import Booking
from sqlalchemy.orm import Session

def create_booking(db: Session, data: dict):
    booking = Booking(**data)
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking

def update_booking_payment_status(db: Session, booking_id: int, payment_status: str = "paid"):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if booking:
        booking.payment_status = payment_status
        db.commit()
        db.refresh(booking)
    return booking
