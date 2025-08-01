import os
import logging
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv
from amadeus import Client, ResponseError

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)

# Environment/config setup
AMADEUS_CLIENT_ID = os.getenv("AMADEUS_CLIENT_ID")
AMADEUS_CLIENT_SECRET = os.getenv("AMADEUS_CLIENT_SECRET")
AMADEUS_ENV = os.getenv("AMADEUS_ENV", "test")  # or "production"
USE_MOCK_FLIGHT_SEARCH = os.getenv("USE_MOCK_FLIGHT_SEARCH", "true").lower() == "true"
USE_MOCK_HOTEL_SEARCH = os.getenv("USE_MOCK_HOTEL_SEARCH", "true").lower() == "true"

amadeus = Client(
    client_id=AMADEUS_CLIENT_ID,
    client_secret=AMADEUS_CLIENT_SECRET,
    hostname="production" if AMADEUS_ENV == "production" else "test",
)

# Optional: known good cities for hotel search (for mock/demo/dev)
WORKING_HOTEL_CITIES = ['NYC', 'LON', 'DEL', 'BOM', 'DXB', 'PAR', 'IST', 'MAN', 'SFO', 'SIN']


def city_to_iata_code(city_name: str) -> Optional[str]:
    """Use Amadeus API to dynamically find IATA code for a given city."""
    try:
        response = amadeus.reference_data.locations.get(
            keyword=city_name, subType="CITY"
        )
        locations = response.data
        if locations:
            return locations[0]["iataCode"]
        return None
    except ResponseError as e:
        logging.error(f"[Amadeus City Lookup Error] {e}")
        return None


def search_flights(origin: str, destination: str, departure_date: str):
    """
    Search for flights using Amadeus API or mock data based on env.
    """
    if USE_MOCK_FLIGHT_SEARCH:
        logging.info("Using mock flight search data (USE_MOCK_FLIGHT_SEARCH=true)")
        try:
            departure_datetime = datetime.strptime(departure_date, "%Y-%m-%d")
        except ValueError:
            logging.error(f"[Mock Flight Search] Invalid departure_date format: {departure_date}")
            return {"error": "Invalid date format. Use YYYY-MM-DD."}
        arrival_datetime = departure_datetime + timedelta(hours=2)
        return [
            {
                "type": "flight-offer",
                "id": "mock1",
                "source": "MOCK",
                "itineraries": [
                    {
                        "duration": "PT2H",
                        "segments": [
                            {
                                "departure": {
                                    "iataCode": origin,
                                    "at": departure_datetime.isoformat()
                                },
                                "arrival": {
                                    "iataCode": destination,
                                    "at": arrival_datetime.isoformat()
                                },
                                "carrierCode": "MO",
                                "number": "123",
                                "duration": "PT2H"
                            }
                        ]
                    }
                ],
                "price": {
                    "total": "100.00",
                    "currency": "USD"
                }
            }
        ]
    # Real Amadeus API call
    logging.info("Using Amadeus flight search (USE_MOCK_FLIGHT_SEARCH=false)")
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
        logging.error(f"[Amadeus Flight Search Error] {e}")
        return {"error": str(e)}


def validate_flight_offer(flight_offer):
    """
    Validate the selected flight offer using Amadeus Flight Offers Price API.
    """
    try:
        payload = {"data": {"type": "flight-offers-pricing", "flightOffers": [flight_offer]}}
        response = amadeus.shopping.flight_offers.pricing.post(payload)
        return response.data
    except ResponseError as error:
        logging.error(f"[Amadeus Flight Offer Validation Error] {error}")
        return {"error": str(error)}


def get_valid_city_codes():
    """Fetch valid city codes from Amadeus API."""
    try:
        city_codes = []
        keywords = ["hotel", "city", "airport"]
        for keyword in keywords:
            response = amadeus.reference_data.locations.get(keyword=keyword, subType="CITY")
            if not response.data:
                continue
            city_codes.extend([location['iataCode'] for location in response.data if 'iataCode' in location])
        unique_city_codes = list(set(city_codes))
        logging.info(f"Fetched {len(unique_city_codes)} unique city codes from Amadeus API")
        logging.info(f"Sample city codes: {unique_city_codes[:10]}")
        return unique_city_codes
    except ResponseError as error:
        logging.error(f"[Amadeus City Codes Fetch Error] {error}")
        return []


def search_hotels(city_code=None, check_in_date=None, check_out_date=None, adults=1):
    if not city_code or len(city_code) != 3:
        logging.error(f"[Amadeus Hotel Search] Invalid or missing city code: {city_code}")
        return []

    try:
        if USE_MOCK_HOTEL_SEARCH:
            logging.info("Using mock hotel search data due to sandbox or limited API plan.")
            return mock_hotel_search(city_code, check_in_date, check_out_date, adults)

        # Validate city codes only once and cache it
        if not hasattr(search_hotels, "_valid_city_codes"):
            search_hotels._valid_city_codes = get_valid_city_codes()

        if city_code not in search_hotels._valid_city_codes:
            logging.error(f"[Amadeus Hotel Search] City code not in Amadeus valid list: {city_code}")
            return []

        if city_code not in WORKING_HOTEL_CITIES:
            logging.warning(f"[Amadeus Hotel Search]No hotel data expected for city: {city_code}")
            return []

        logging.info(f"🔍 Searching hotels for cityCode={city_code}, checkInDate={check_in_date}, checkOutDate={check_out_date}, adults={adults}")

        params = {
            "cityCode": city_code,
            "checkInDate": check_in_date,
            "checkOutDate": check_out_date,
            "adults": adults,
            "roomQuantity": 1,
            "bestRateOnly": True,
            "paymentPolicy": "NONE",
            "includeClosed": False,
            "view": "FULL"
        }

        response = amadeus.shopping.hotel_offers_search.get(**params)
        logging.info(f"Amadeus responded: {response.status_code}")

        if not response.data:
            logging.warning(f"[Amadeus Hotel Search]No hotel data returned.")
            return []

        hotels = []
        for offer in response.data:
            hotel = offer.get("hotel", {})
            first_offer = offer.get("offers", [{}])[0]
            price_info = first_offer.get("price", {})

            hotels.append({
                "name": hotel.get("name"),
                "cityCode": hotel.get("cityCode"),
                "checkInDate": check_in_date,
                "checkOutDate": check_out_date,
                "adults": adults,
                "price": price_info.get("total", "N/A"),
                "currency": price_info.get("currency", "USD")
            })

        return hotels

    except ResponseError as error:
        logging.error(f"[Amadeus Hotel Error]{error}")
        if hasattr(error, 'response'):
            try:
                logging.error("Amadeus Error Response: %s", error.response.data)
            except Exception:
                logging.error("No detailed response data available")

        if hasattr(error, 'response') and error.response.status_code == 400:
            logging.error("[Hotel Search]Bad request — possibly unsupported city. Returning empty list.")
            return []

        return []


def mock_hotel_search(city_code, check_in_date, check_out_date, adults=1):
    logging.info(f"Mocking hotel search for cityCode={city_code}, checkInDate={check_in_date}, checkOutDate={check_out_date}, adults={adults}")
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


def check_api_plan_and_environment():
    # This is a placeholder function to check API plan or environment restrictions
    logging.info("Checking Amadeus API plan and environment settings...")
    plan = "sandbox"
    restrictions = ["limited hotel data"]
    logging.info(f"API plan: {plan}")
    logging.info(f"Known restrictions: {restrictions}")
    return plan, restrictions


def verify_amadeus_credentials():
    try:
        test_response = amadeus.reference_data.locations.get(keyword="NYC", subType="CITY")
        logging.info(f"Amadeus API credentials verified. Sample location data: {test_response.data}")
        return True
    except ResponseError as error:
        logging.error(f"[Amadeus Credential Verification Error] {error}")
        return False


def create_flight_order(order_data, travelers):
    try:
        logging.info("Simulating flight booking in sandbox environment.")
        simulated_response = {
            "type": "flight-order",
            "id": "simulated_order_123",
            "status": "CONFIRMED",
            "flightOffers": order_data.get("flightOffers", []),
            "travelers": travelers
        }
        return simulated_response
        # To use real API in production, uncomment below if you have Enterprise access:
        # response = amadeus.booking.flight_orders.post(order_data, travelers)
        # return response.data
    except ResponseError as error:
        logging.error(f"[Amadeus Flight Booking Error] {error}")
        if hasattr(error, 'response'):
            try:
                logging.error(f"Response content: {error.response.data}")
            except Exception:
                logging.error("No response data available")
        else:
            import traceback
            logging.error("Full traceback:")
            traceback.print_exc()
        return None


def create_hotel_booking(booking_data, guests, payments):
    try:
        logging.info("Simulating hotel booking in sandbox environment.")
        simulated_response = {
            "type": "hotel-booking",
            "id": "simulated_booking_123",
            "status": "CONFIRMED",
            "bookingData": booking_data,
            "guests": guests,
            "payments": payments
        }
        return simulated_response
        # To use real API in production, uncomment below if you have Enterprise access:
        # response = amadeus.booking.hotel_bookings.post(booking_data, guests, payments)
        # return response.data
    except ResponseError as error:
        logging.error(f"[Amadeus Hotel Booking Error] {error}")
        if hasattr(error, 'response'):
            try:
                logging.error(f"Response content: {error.response.data}")
            except Exception:
                logging.error("No response data available")
        return None
