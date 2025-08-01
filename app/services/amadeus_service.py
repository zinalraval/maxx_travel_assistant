from amadeus import Client, ResponseError
from app.config import settings
import os
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

AMADEUS_CLIENT_ID = os.getenv("AMADEUS_CLIENT_ID")
AMADEUS_CLIENT_SECRET = os.getenv("AMADEUS_CLIENT_SECRET")
AMADEUS_ENV = os.getenv("AMADEUS_ENV", "test")  # or "production"

amadeus = Client(
    client_id=AMADEUS_CLIENT_ID,
    client_secret=AMADEUS_CLIENT_SECRET,
    hostname="production" if AMADEUS_ENV == "production" else "test",
)

USE_MOCK_FLIGHT_SEARCH = os.getenv("USE_MOCK_FLIGHT_SEARCH", "true").lower() == "true"
USE_MOCK_HOTEL_SEARCH = os.getenv("USE_MOCK_HOTEL_SEARCH", "true").lower() == "true"


def city_to_iata_code(city_name: str) -> Optional[str]:
    """
    Use Amadeus API to dynamically find IATA code for a given city.
    """
    try:
        response = amadeus.reference_data.locations.get(
            keyword=city_name, subType="CITY"
        )
        locations = response.data
        if locations:
            return locations[0]["iataCode"]
        return None
    except ResponseError as e:
        print(f"[Amadeus City Lookup Error] {e}")
        return None


def search_flights(origin: str, destination: str, departure_date: str):
    """
    Search for flights using Amadeus API or mock data based on env.
    """
    if USE_MOCK_FLIGHT_SEARCH:
        print("🔁 Using mock flight search data (USE_MOCK_FLIGHT_SEARCH=true)")
        try:
            departure_datetime = datetime.strptime(departure_date, "%Y-%m-%d")
        except ValueError:
            print(f"[Mock Flight Search] Invalid departure_date format: {departure_date}")
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
    print("Using Amadeus flight search (USE_MOCK_FLIGHT_SEARCH=false)")
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
        print(f"[Amadeus Flight Search Error] {e}")
        return {"error": str(e)}
        
valid_city_codes_cache = None
USE_MOCK_HOTEL_SEARCH = os.getenv("USE_MOCK_HOTEL_SEARCH", "false").lower() == "true"

from amadeus import ResponseError
from amadeus import Client

def get_valid_city_codes():
    # This function should be implemented here or imported from a valid module
    # For now, return a hardcoded list or fetch dynamically if possible
    return ['NYC', 'LON', 'DEL', 'BOM', 'DXB', 'PAR', 'IST', 'MAN', 'SFO', 'SIN']

amadeus = Client(
    client_id=settings.AMADEUS_CLIENT_ID,
    client_secret=settings.AMADEUS_CLIENT_SECRET
)


# Optional: known good cities for hotel search
WORKING_HOTEL_CITIES = ['NYC', 'LON', 'DEL', 'BOM', 'DXB', 'PAR', 'IST', 'MAN', 'SFO', 'SIN']

def search_hotels(city_code=None, check_in_date=None, check_out_date=None, adults=1):
    if not city_code or len(city_code) != 3:
        print(f"[Amadeus Hotel Search] ❌ Invalid or missing city code: {city_code}")
        return []

    try:
        if USE_MOCK_HOTEL_SEARCH:
            print("Using mock hotel search data due to sandbox or limited API plan.")
            return mock_hotel_search(city_code, check_in_date, check_out_date, adults)

        # Validate city codes only once and cache it
        if not hasattr(search_hotels, "_valid_city_codes"):
            search_hotels._valid_city_codes = get_valid_city_codes()

        if city_code not in search_hotels._valid_city_codes:
            print(f"[Amadeus Hotel Search] ❌ City code not in Amadeus valid list: {city_code}")
            return []

        if city_code not in WORKING_HOTEL_CITIES:
            print(f"[Amadeus Hotel Search] ⚠️ No hotel data expected for city: {city_code}")
            return []

        print(f"🔍 Searching hotels for cityCode={city_code}, checkInDate={check_in_date}, checkOutDate={check_out_date}, adults={adults}")

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
        print(f"Amadeus responded: {response.status_code}")

        if not response.data:
            print(f"[Amadeus Hotel Search] ⚠️ No hotel data returned.")
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
        print(f"[Amadeus Hotel Error] ❌ {error}")
        if hasattr(error, 'response'):
            try:
                print("📦 Amadeus Error Response:", error.response.data)
            except Exception:
                print("⚠️ No detailed response data available")

        if hasattr(error, 'response') and error.response.status_code == 400:
            print("[Hotel Search] ❌ Bad request — possibly unsupported city. Returning empty list.")
            return []

        return []

def get_valid_city_codes():
    try:
        city_codes = []
        keywords = ["hotel", "city", "airport"]
        for keyword in keywords:
            response = amadeus.reference_data.locations.get(keyword=keyword, subType="CITY")
            if not response.data:
                continue
            city_codes.extend([location['iataCode'] for location in response.data if 'iataCode' in location])
        unique_city_codes = list(set(city_codes))
        print(f"Fetched {len(unique_city_codes)} unique city codes from Amadeus API")
        print(f"Sample city codes: {unique_city_codes[:10]}")
        return unique_city_codes
    except ResponseError as error:
        print(f"[Amadeus City Codes Fetch Error] {error}")
        return []

def mock_hotel_search(city_code, check_in_date, check_out_date, adults=1):
    print(f"Mocking hotel search for cityCode={city_code}, checkInDate={check_in_date}, checkOutDate={check_out_date}, adults={adults}")
    # Return a sample mocked hotel list
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
    # You may want to check your Amadeus developer dashboard or API keys for plan details
    print("Checking Amadeus API plan and environment settings...")
    # Simulate check result
    plan = "sandbox"
    restrictions = ["limited hotel data"]
    print(f"API plan: {plan}")
    print(f"Known restrictions: {restrictions}")
    return plan, restrictions

def verify_amadeus_credentials():
    try:
        test_response = amadeus.reference_data.locations.get(keyword="NYC", subType="CITY")
        print(f"Amadeus API credentials verified. Sample location data: {test_response.data}")
        return True
    except ResponseError as error:
        print(f"[Amadeus Credential Verification Error] {error}")
        return False

def get_valid_city_codes():
    try:
        city_codes = []
        keywords = ["hotel", "city", "airport"]
        for keyword in keywords:
            response = amadeus.reference_data.locations.get(keyword=keyword, subType="CITY")
            if not response.data:
                continue
            city_codes.extend([location['iataCode'] for location in response.data if 'iataCode' in location])
        unique_city_codes = list(set(city_codes))
        print(f"Fetched {len(unique_city_codes)} unique city codes from Amadeus API")
        print(f"Sample city codes: {unique_city_codes[:10]}")
        return unique_city_codes
    except ResponseError as error:
        print(f"[Amadeus City Codes Fetch Error] {error}")
        return []


import logging

def create_flight_order(order_data, travelers):
    try:
        # Simulate booking in sandbox environment
        print("Simulating flight booking in sandbox environment.")
        simulated_response = {
            "type": "flight-order",
            "id": "simulated_order_123",
            "status": "CONFIRMED",
            "flightOffers": order_data.get("flightOffers", []),
            "travelers": travelers
        }
        return simulated_response
        # Uncomment below to use real API call if Enterprise plan is available
        # response = amadeus.booking.flight_orders.post(order_data, travelers)
        # return response.data
    except ResponseError as error:
        print(f"[Amadeus Flight Booking Error] {error}")
        if hasattr(error, 'response'):
            try:
                print(f"Response content: {error.response.data}")
            except Exception:
                print("No response data available")
        else:
            import traceback
            print("Full traceback:")
            traceback.print_exc()
        return None

def create_hotel_booking(booking_data, guests, payments):
    try:
        # Simulate hotel booking in sandbox environment
        print("Simulating hotel booking in sandbox environment.")
        simulated_response = {
            "type": "hotel-booking",
            "id": "simulated_booking_123",
            "status": "CONFIRMED",
            "bookingData": booking_data,
            "guests": guests,
            "payments": payments
        }
        return simulated_response
        # Uncomment below to use real API call if Enterprise plan is available
        # response = amadeus.booking.hotel_bookings.post(booking_data, guests, payments)
        # return response.data
    except ResponseError as error:
        print(f"[Amadeus Hotel Booking Error] {error}")
        if hasattr(error, 'response'):
            try:
                print(f"Response content: {error.response.data}")
            except Exception:
                print("No response data available")
        return None
