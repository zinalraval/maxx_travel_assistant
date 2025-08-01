import os
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv
from amadeus import Client, ResponseError
from app.config import settings

# Load .env variables
load_dotenv()

# Amadeus configuration
AMADEUS_CLIENT_ID = os.getenv("AMADEUS_CLIENT_ID", settings.AMADEUS_CLIENT_ID)
AMADEUS_CLIENT_SECRET = os.getenv("AMADEUS_CLIENT_SECRET", settings.AMADEUS_CLIENT_SECRET)
AMADEUS_ENV = os.getenv("AMADEUS_ENV", "test")  # "production" or "test"

# Environment-based mock toggles
USE_MOCK_FLIGHT_SEARCH = os.getenv("USE_MOCK_FLIGHT_SEARCH", "false").lower() == "true"

# Initialize Amadeus client
amadeus = Client(
    client_id=AMADEUS_CLIENT_ID,
    client_secret=AMADEUS_CLIENT_SECRET,
    hostname="production" if AMADEUS_ENV == "production" else "test",
)


def city_to_iata_code(city_name: str) -> Optional[str]:
    """
    Use Amadeus API to find IATA code from city name.
    """
    try:
        response = amadeus.reference_data.locations.get(
            keyword=city_name,
            subType="CITY"
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
    Search for flights using Amadeus or fallback mock data.
    """
    if USE_MOCK_FLIGHT_SEARCH:
        print("🔁 Using mock flight search data (USE_MOCK_FLIGHT_SEARCH=true)")

        try:
            departure_datetime = datetime.strptime(departure_date, "%Y-%m-%d")
        except ValueError:
            return {"error": "Invalid departure date format. Use YYYY-MM-DD."}

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
                                "aircraft": {"code": "321"},
                                "duration": "PT2H"
                            }
                        ]
                    }
                ],
                "price": {
                    "currency": "USD",
                    "total": "100.00",
                    "base": "85.00"
                },
                "travelerPricings": [
                    {
                        "travelerId": "1",
                        "fareOption": "STANDARD",
                        "price": {
                            "currency": "USD",
                            "total": "100.00",
                            "base": "85.00"
                        },
                        "fareDetailsBySegment": [
                            {
                                "segmentId": "1",
                                "cabin": "ECONOMY",
                                "fareBasis": "Y",
                                "class": "Y",
                                "includedCheckedBags": {
                                    "quantity": 1
                                }
                            }
                        ]
                    }
                ]
            }
        ]

    # Actual Amadeus request
    try:
        print("Querying Amadeus API (real response)...")
        response = amadeus.shopping.flight_offers_search.get(
            originLocationCode=origin,
            destinationLocationCode=destination,
            departureDate=departure_date,
            adults=1,
            max=5
        )
        return response.data
    except ResponseError as e:
        print(f"[Amadeus API Error] {e}")
        return {"error": str(e)}
