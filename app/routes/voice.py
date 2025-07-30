from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import os
import re
import requests
from datetime import datetime
from dateutil import parser as date_parser
from pydantic import BaseModel
import logging

router = APIRouter()

# Logging
logger = logging.getLogger("uvicorn")
logger.setLevel(logging.INFO)

# Offline map for fallback
CITY_TO_IATA = {
    "mumbai": "BOM",
    "delhi": "DEL",
    "london": "LON",
    "new york": "NYC",
    "dubai": "DXB",
    "paris": "PAR",
}

AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET")
AMADEUS_TOKEN = None

def get_amadeus_token():
    global AMADEUS_TOKEN
    if AMADEUS_TOKEN:
        return AMADEUS_TOKEN
    try:
        resp = requests.post(
            "https://test.api.amadeus.com/v1/security/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": AMADEUS_API_KEY,
                "client_secret": AMADEUS_API_SECRET
            },
            timeout=5
        )
        if resp.status_code == 200:
            AMADEUS_TOKEN = resp.json()["access_token"]
            return AMADEUS_TOKEN
    except Exception as e:
        logger.error(f"Amadeus token fetch error: {e}")
    return None

def resolve_iata(city: str):
    if not city:
        return None
    city = city.lower().strip()

    if city in CITY_TO_IATA:
        return CITY_TO_IATA[city]

    token = get_amadeus_token()
    if not token:
        return None

    try:
        resp = requests.get(
            "https://test.api.amadeus.com/v1/reference-data/locations",
            params={"keyword": city, "subType": "CITY"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=5
        )
        results = resp.json().get("data", [])
        if results:
            return results[0]["iataCode"]
    except Exception as e:
        logger.error(f"IATA resolution error for {city}: {e}")
    return None

def extract_info(text: str):
    origin, destination, city, date_str = None, None, None, None
    text = text.lower()

    flight_match = re.search(r"from\s+([\w\s]+)\s+to\s+([\w\s]+)", text)
    hotel_match = re.search(r"hotel\s+in\s+([\w\s]+)", text)
    date_match = re.search(r"on\s+([a-zA-Z0-9\s,]+)", text)

    if flight_match:
        origin = flight_match.group(1).strip()
        destination = flight_match.group(2).strip()
    elif hotel_match:
        city = hotel_match.group(1).strip()

    if date_match:
        try:
            parsed_date = date_parser.parse(date_match.group(1), fuzzy=True)
            # Ensure correct year
            now = datetime.now()
            if parsed_date.year < now.year:
                parsed_date = parsed_date.replace(year=now.year)
            date_str = parsed_date.strftime("%Y-%m-%d")
        except Exception as e:
            logger.warning(f"Date parsing failed: {e}")
            date_str = None

    return origin, destination, city, date_str

@router.post("/voice/voice-webhook")
async def voice_webhook(request: Request):
    try:
        data = await request.json()

        logger.info("=== MILLIS DEBUG ===")
        logger.info(f"Received: {data}")
        logger.info("====================")

        voice_text = data.get("text") or data.get("voice_text") or ""
        metadata = data.get("metadata", {})
        session_id = data.get("session_id") or "unknown"

        origin = metadata.get("origin")
        destination = metadata.get("destination")
        city = metadata.get("city")
        date_str = metadata.get("date")
        adults = metadata.get("adults", 1)

        if date_str:
            try:
                parsed_date = date_parser.parse(date_str, fuzzy=True)
                if parsed_date.year < datetime.now().year:
                    parsed_date = parsed_date.replace(year=datetime.now().year)
                date_str = parsed_date.strftime("%Y-%m-%d")
            except Exception as e:
                logger.warning(f"Metadata date parse failed: {e}")
                date_str = None

        if not origin or not destination or not date_str:
            f_origin, f_dest, f_city, f_date = extract_info(voice_text)
            origin = origin or f_origin
            destination = destination or f_dest
            city = city or f_city
            date_str = date_str or f_date

        # === Flight Search ===
        if origin and destination and date_str:
            origin_code = resolve_iata(origin)
            dest_code = resolve_iata(destination)

            if not origin_code or not dest_code:
                return {"response_text": f"Couldn’t find airport codes for {origin} or {destination}. Try again."}

            resp = requests.get(
                "https://maxx-travel-assistant.onrender.com/booking/flights",
                params={"origin": origin_code, "destination": dest_code, "date": date_str, "session_id": session_id},
                timeout=10
            )
            result = resp.json()
            if result.get("flights"):
                flight = result["flights"][0]
                return {
                    "response_text": f"The best flight from {origin.title()} to {destination.title()} on {date_str} is {flight['airline']} flight {flight['flight_number']} for ₹{flight['price']}."
                }
            return {"response_text": f"No flights found from {origin.title()} to {destination.title()} on {date_str}."}

        # === Hotel Search ===
        elif city and date_str:
            city_code = resolve_iata(city)
            if not city_code:
                return {"response_text": f"I couldn’t find an airport near {city.title()}. Try another city."}

            resp = requests.get(
                "https://maxx-travel-assistant.onrender.com/booking/hotels",
                params={
                    "city_code": city_code,
                    "check_in_date": date_str,
                    "check_out_date": date_str,
                    "adults": adults,
                    "session_id": session_id
                },
                timeout=10
            )
            result = resp.json()
            if result.get("hotels"):
                hotel = result["hotels"][0]
                return {
                    "response_text": f"I found {hotel['name']} in {city.title()} for ₹{hotel['price']} per night."
                }
            return {"response_text": f"No hotels found in {city.title()} on {date_str}."}

        return {
            "response_text": "Please say something like 'Book flight from Delhi to Dubai on August 15' or 'Find hotel in Paris on August 10'."
        }

    except Exception as e:
        logger.error(f"Unhandled error in voice_webhook: {e}")
        return JSONResponse(status_code=500, content={"response_text": "An error occurred while processing your request. Please try again later."})
