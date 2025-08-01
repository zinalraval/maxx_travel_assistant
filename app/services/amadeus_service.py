import os
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv
from amadeus import Client, ResponseError

load_dotenv()

AMADEUS_CLIENT_ID = os.getenv("AMADEUS_CLIENT_ID")
AMADEUS_CLIENT_SECRET = os.getenv("AMADEUS_CLIENT_SECRET")
AMADEUS_ENV = os.getenv("AMADEUS_ENV", "test")  # "test" or "production"

USE_MOCK_FLIGHT_SEARCH = os.getenv("USE_MOCK_FLIGHT_SEARCH", "false").lower() == "true"
USE_MOCK_HOTEL_SEARCH = os.getenv("USE_MOCK_HOTEL_SEARCH", "false").lower() == "true"

amadeus = Client(
    client_id=AMADEUS_CLIENT_ID,
    client_secret=AMADEUS_CLIENT_SECRET,
    hostname="production" if AMADEUS_ENV == "production" else "test",
)

# ----------- CITY LOOKUP ----------- #

def city_to_iata_code(city_name: str) -> Optional[str]:
    try:
        response = amadeus.reference_data.locations.get(keyword=city_name, subType="CITY")
        if response.data:
            return response.data[0]["iataCode"]
    except ResponseError as e:
        print(f"[City Lookup Error] {e}")
    return None


# ----------- FLIGHT SEARCH ----------- #

def search_flights(origin: str, destination: str, departure_date: str):
    if USE_MOCK_FLIGHT_SEARCH:
        print("Using mock flight search data.")
        try:
            departure = datetime.strptime(departure_date, "%Y-%m-%d")
        except ValueError:
            return {"error": "Invalid date format. Use YYYY-MM-DD."}

        return [
            {
                "type": "flight-offer",
                "id": "mock1",
                "source": "MOCK",
                "itineraries": [{
                    "duration": "PT2H",
                    "segments": [{
                        "departure": {"iataCode": origin, "at": departure.isoformat()},
                        "arrival": {"iataCode": destination, "at": (departure + timedelta(hours=2)).isoformat()},
                        "carrierCode": "MO", "number": "123", "duration": "PT2H"
                    }]
                }],
                "price": {"total": "100.00", "currency": "USD"}
            }
        ]

    try:
        response = amadeus.shopping.flight_offers_search.get(
            originLocationCode=origin,
            destinationLocationCode=destination,
            departureDate=departure_date,
            adults=1,
            max=5
        )
        return response.data
    except ResponseError as e:
        print(f"[Flight Search Error] {e}")
        return {"error": str(e)}


# ----------- HOTEL SEARCH ----------- #

WORKING_HOTEL_CITIES = ['NYC', 'LON', 'DEL', 'BOM', 'DXB', 'PAR', 'IST', 'MAN', 'SFO', 'SIN']

def search_hotels(city_code, check_in_date, check_out_date, adults=1):
    if not city_code or len(city_code) != 3:
        print(f"[Hotel Search] Invalid city code: {city_code}")
        return []

    if USE_MOCK_HOTEL_SEARCH:
        return mock_hotel_search(city_code, check_in_date, check_out_date, adults)

    try:
        response = amadeus.shopping.hotel_offers_search.get(
            cityCode=city_code,
            checkInDate=check_in_date,
            checkOutDate=check_out_date,
            adults=adults,
            roomQuantity=1,
            bestRateOnly=True,
            paymentPolicy="NONE",
            includeClosed=False,
            view="FULL"
        )
        if not response.data:
            return []

        hotels = []
        for offer in response.data:
            hotel = offer.get("hotel", {})
            first_offer = offer.get("offers", [{}])[0]
            price = first_offer.get("price", {})
            hotels.append({
                "name": hotel.get("name"),
                "cityCode": hotel.get("cityCode"),
                "checkInDate": check_in_date,
                "checkOutDate": check_out_date,
                "adults": adults,
                "price": price.get("total", "N/A"),
                "currency": price.get("currency", "USD")
            })

        return hotels

    except ResponseError as e:
        print(f"[Hotel Search Error] {e}")
        return []


def mock_hotel_search(city_code, check_in_date, check_out_date, adults=1):
    return [
        {
            "hotelName": "Mock Hotel 1",
            "cityCode": city_code,
            "checkInDate": check_in_date,
            "checkOutDate": check_out_date,
            "adults": adults,
            "price": 100.0,
            "currency": "USD"
        },
        {
            "hotelName": "Mock Hotel 2",
            "cityCode": city_code,
            "checkInDate": check_in_date,
            "checkOutDate": check_out_date,
            "adults": adults,
            "price": 150.0,
            "currency": "USD"
        }
    ]


# ----------- FLIGHT ORDER SIMULATION ----------- #

def create_flight_order(order_data, travelers):
    try:
        print("Simulating flight order booking...")
        return {
            "type": "flight-order",
            "id": "simulated_order_123",
            "status": "CONFIRMED",
            "flightOffers": order_data.get("flightOffers", []),
            "travelers": travelers
        }
    except ResponseError as e:
        print(f"[Flight Booking Error] {e}")
        return None


# ----------- HOTEL ORDER SIMULATION ----------- #

def create_hotel_booking(booking_data, guests, payments):
    try:
        print("Simulating hotel booking...")
        return {
            "type": "hotel-booking",
            "id": "simulated_booking_123",
            "status": "CONFIRMED",
            "bookingData": booking_data,
            "guests": guests,
            "payments": payments
        }
    except ResponseError as e:
        print(f"[Hotel Booking Error] {e}")
        return None


# ----------- HELPER: VERIFY CREDENTIALS ----------- #

def verify_amadeus_credentials():
    try:
        response = amadeus.reference_data.locations.get(keyword="NYC", subType="CITY")
        print(f"Verified Amadeus credentials: {response.data[:1]}")
        return True
    except ResponseError as e:
        print(f"[Credential Verification Error] {e}")
        return False
