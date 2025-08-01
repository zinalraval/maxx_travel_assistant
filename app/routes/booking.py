from fastapi import APIRouter, Query, Depends, Request, Body, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.services.stripe_service import create_checkout_session
from app.services.amadeus_service import search_flights, search_hotels, create_flight_order, create_hotel_booking, validate_flight_offer
from app.services.calendar_service import create_event
from app.db.crud import create_booking, update_booking_payment_status
from app.db.session import SessionLocal
from app.models.booking import Booking
from app.schemas.booking import BookingCreate, FlightBookingRequest, HotelBookingRequest
from sqlalchemy.orm import Session
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

CITY_CODE_MAP = {
    "LON": "LHR", "NYC": "JFK", "PAR": "CDG",
    "DEL": "DEL", "BOM": "BOM", "DXB": "DXB",
    "IST": "IST", "MAN": "MAN", "SFO": "SFO", "SIN": "SIN"
}

def normalize_city_code(code: str) -> str:
    return CITY_CODE_MAP.get(code.upper(), code.upper())

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
        normalized_origin = normalize_city_code(origin)
        normalized_destination = normalize_city_code(destination)
        try:
            travel_date = datetime.strptime(date, "%Y-%m-%d").date()
            today = datetime.utcnow().date()
            if travel_date < today:
                logger.warning(f"Past date provided: {date}")
                raise HTTPException(status_code=400, detail=f"Cannot search flights in the past: {date}")
        except Exception as date_error:
            logger.error(f"Invalid date format: {date} - {date_error}")
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
        flights = search_flights(normalized_origin, normalized_destination, date)
        if not flights:
            logger.warning(f"No flights found for {normalized_origin} to {normalized_destination} on {date}")
            raise HTTPException(status_code=404, detail=f"No flights found for {normalized_origin} to {normalized_destination} on {date}")
        return {"flights": flights}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching flights: {e}")
        raise HTTPException(status_code=500, detail="Failed to search flights")

@router.post("/validate-flight-offer")
async def validate_flight_offer_route(flight_offer: dict = Body(...)):
    try:
        validated_offer = validate_flight_offer(flight_offer)
        return {"success": True, "validated_offer": validated_offer}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Validation failed: {str(e)}")

@router.post("/pay")
def initiate_payment(payment_request: PaymentRequest):
    try:
        url = create_checkout_session(payment_request.amount)
        if url:
            return {"checkout_url": url}
        else:
            logger.error("Payment session could not be created.")
            raise HTTPException(status_code=500, detail="Payment session could not be created.")
    except Exception as e:
        logger.error(f"Error initiating payment: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate payment")

@router.get("/hotels")
def get_hotels(
    city_code: str,
    check_in_date: str,
    check_out_date: str,
    adults: int = 1,
    session_id: str = Query(None)
):
    try:
        normalized_city_code = normalize_city_code(city_code)
        hotels = search_hotels(normalized_city_code, check_in_date, check_out_date, adults)
        if not hotels:
            logger.warning(f"No hotels found for city {normalized_city_code} from {check_in_date} to {check_out_date}")
            raise HTTPException(status_code=404, detail="No hotels found")
        return {"hotels": hotels}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching hotels: {e}")
        raise HTTPException(status_code=500, detail=f"Exception occurred: {str(e)}")

@router.post("/flight-book")
def book_flight(flight_booking: FlightBookingRequest = Body(...), session_id: str = Query(...)):
    try:
        # Validate the flight offer before booking
        try:
            validate_flight_offer(flight_booking.order_data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Flight offer validation failed: {str(e)}")
        logger.info(f"Booking flight with order_data: {flight_booking.order_data}")
        logger.info(f"Travelers: {flight_booking.travelers}")
        result = create_flight_order(flight_booking.order_data, flight_booking.travelers)
        logger.info(f"Flight booking result: {result}")
        if not result:
            logger.error("Flight booking failed")
            raise HTTPException(status_code=500, detail="Flight booking failed")
        return {"booking": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Exception during flight booking: {e}")
        raise HTTPException(status_code=500, detail="Flight booking exception occurred")

@router.post("/hotel-book")
def book_hotel(hotel_booking: HotelBookingRequest = Body(...), session_id: str = Query(...)):
    try:
        result = create_hotel_booking(hotel_booking.booking_data, hotel_booking.guests, None)
        if not result:
            logger.error("Hotel booking failed")
            raise HTTPException(status_code=500, detail="Hotel booking failed")
        return {"booking": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Exception during hotel booking: {e}")
        raise HTTPException(status_code=500, detail="Hotel booking exception occurred")

@router.post("/confirm")
def confirm_booking(booking: BookingCreate = Body(...), db: Session = Depends(get_db)):
    try:
        booking_data = Booking(**booking.model_dump())
        saved = create_booking(db, booking.model_dump())
        return {"message": "Booking stored", "booking_id": saved.id}
    except Exception as e:
        logger.error(f"Error confirming booking: {e}")
        raise HTTPException(status_code=500, detail="Failed to confirm booking")

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
        raise HTTPException(status_code=500, detail=str(e))
