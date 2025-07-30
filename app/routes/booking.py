from fastapi import APIRouter, Query, Depends, Request, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.services.stripe_service import create_checkout_session
from app.services.amadeus_service import search_flights, search_hotels, create_flight_order, create_hotel_booking
from app.services.calendar_service import create_event
from app.db.crud import create_booking, update_booking_payment_status
from app.db.session import SessionLocal
from app.models.booking import Booking
from app.schemas.booking import BookingCreate, FlightBookingRequest, HotelBookingRequest
from sqlalchemy.orm import Session
import logging

from app.services.amadeus_service import get_valid_city_codes

router = APIRouter()
logger = logging.getLogger(__name__)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class PaymentRequest(BaseModel):
    amount: float

@router.get("/flights")
def get_flights(
    origin: str = Query(..., alias="originLocationCode"),
    destination: str = Query(..., alias="destinationLocationCode"),
    date: str = Query(..., alias="departureDate"),
    session_id: str = Query(...)
):
    try:
        # Normalize city codes for flight search
        city_code_map = {
            "LON": "LHR",  # London Heathrow instead of Gatwick
            "NYC": "JFK",  # New York JFK
            "DEL": "DEL",
            "BOM": "BOM",
            "DXB": "DXB",
            "PAR": "CDG",  # Paris Charles de Gaulle
            "IST": "IST",
            "MAN": "MAN",
            "SFO": "SFO",
            "SIN": "SIN"
        }
        normalized_origin = city_code_map.get(origin.upper(), origin.upper())
        normalized_destination = city_code_map.get(destination.upper(), destination.upper())

        flights = search_flights(normalized_origin, normalized_destination, date)
        if not flights:
            logger.warning(f"No flights found for {normalized_origin} to {normalized_destination} on {date}")
            return {"error": "No flights found"}
        return {"flights": flights}
    except Exception as e:
        logger.error(f"Error searching flights: {e}")
        return {"error": "Failed to search flights"}

@router.post("/pay")
def initiate_payment(payment_request: PaymentRequest):
    try:
        url = create_checkout_session(payment_request.amount)
        if url:
            return {"checkout_url": url}
        else:
            logger.error("Payment session could not be created.")
            return {"error": "Payment session could not be created."}
    except Exception as e:
        logger.error(f"Error initiating payment: {e}")
        return {"error": "Failed to initiate payment"}

@router.get("/hotels")
def get_hotels(
    city_code: str,
    check_in_date: str,
    check_out_date: str,
    adults: int = 1,
    session_id: str = Query(None)
):
    try:
        # Normalize city_code for known aliases
        city_code_map = {
            "LON": "LHR",  # London Heathrow instead of Gatwick
            "NYC": "JFK",  # New York JFK
            "DEL": "DEL",
            "BOM": "BOM",
            "DXB": "DXB",
            "PAR": "CDG",  # Paris Charles de Gaulle
            "IST": "IST",
            "MAN": "MAN",
            "SFO": "SFO",
            "SIN": "SIN"
        }
        normalized_city_code = city_code_map.get(city_code.upper(), city_code.upper())

        hotels = search_hotels(normalized_city_code, check_in_date, check_out_date, adults)
        if not hotels:
            logger.warning(f"No hotels found for city {normalized_city_code} from {check_in_date} to {check_out_date}")
            return {"error": "No hotels found"}
        return {"hotels": hotels}
    except Exception as e:
        logger.error(f"Error searching hotels: {e}")
        return {"error": f"Exception occurred: {str(e)}"}

@router.post("/flight-book")
def book_flight(flight_booking: FlightBookingRequest = Body(...), session_id: str = Query(...)):
    try:
        logger.info(f"Booking flight with order_data: {flight_booking.order_data}")
        logger.info(f"Travelers: {flight_booking.travelers}")
        result = create_flight_order(flight_booking.order_data, flight_booking.travelers)
        logger.info(f"Flight booking result: {result}")
        if not result:
            logger.error("Flight booking failed")
            return {"error": "Flight booking failed"}
        return {"booking": result}
    except Exception as e:
        logger.error(f"Exception during flight booking: {e}")
        return {"error": "Flight booking exception occurred"}

@router.post("/hotel-book")
def book_hotel(hotel_booking: HotelBookingRequest = Body(...), session_id: str = Query(...)):
    try:
        # Assuming payments info is not available, pass None or handle accordingly
        result = create_hotel_booking(hotel_booking.booking_data, hotel_booking.guests, None)
        if not result:
            logger.error("Hotel booking failed")
            return {"error": "Hotel booking failed"}
        return {"booking": result}
    except Exception as e:
        logger.error(f"Exception during hotel booking: {e}")
        return {"error": "Hotel booking exception occurred"}

@router.post("/confirm")
def confirm_booking(booking: BookingCreate = Body(...), db: Session = Depends(get_db)):
    try:
        booking_data = Booking(**booking.model_dump())
        saved = create_booking(db, booking.model_dump())
        return {"message": "Booking stored", "booking_id": saved.id}
    except Exception as e:
        logger.error(f"Error confirming booking: {e}")
        return {"error": "Failed to confirm booking"}

@router.post("/stripe-webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    from app.services.stripe_service import handle_stripe_webhook
    try:
        event = handle_stripe_webhook(payload, sig_header)
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            booking_id = session.get('metadata', {}).get('booking_id')
            if booking_id:
                updated_booking = update_booking_payment_status(db, int(booking_id), payment_status="paid")
                if updated_booking:
                    logger.info(f"Booking {booking_id} payment status updated to paid.")
                else:
                    logger.warning(f"Booking {booking_id} not found.")
            else:
                logger.warning("Booking ID not found in session metadata.")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Stripe webhook error: {e}")
        return {"error": str(e)}
