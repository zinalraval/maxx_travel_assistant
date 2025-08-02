from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import ConfigDict

class BookingCreate(BaseModel):
    user_name: str
    email: str
    phone: str
    origin: Optional[str] = None
    destination: Optional[str] = None
    departure_date: Optional[str] = None
    flight_number: Optional[str] = None
    amount_paid: Optional[float] = None
    payment_status: Optional[str] = "paid"
    booked_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class FlightOfferValidationRequest(BaseModel):
    flight_offer: Dict[str, Any]
    session_id: str

class FlightBookingRequest(BaseModel):
    order_data: Dict[str, Any]
    travelers: List[Dict[str, Any]]

class HotelBookingRequest(BaseModel):
    booking_data: Dict[str, Any]
    guests: List[Dict[str, Any]]
    payments: List[Dict[str, Any]]

class FlightInspirationRequest(BaseModel):
    origin: str

class FlightCheapestDateRequest(BaseModel):
    origin: str
    destination: str

class FlightUpsellingRequest(BaseModel):
    body: Dict[str, Any]

class FlightSeatmapRequest(BaseModel):
    flight_order_id: str

class FlightSeatmapPostRequest(BaseModel):
    body: Dict[str, Any]

class TripPurposePredictionRequest(BaseModel):
    origin: str
    destination: str
    departure_date: str
    return_date: str

class TransferSearchRequest(BaseModel):
    body: Dict[str, Any]

class TransferBookingRequest(BaseModel):
    body: Dict[str, Any]
    offer_id: str
