# app/routes/voice.py

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import os
import re
import requests
from datetime import datetime, timedelta
from dateutil import parser as date_parser

router = APIRouter()

BASE_URL = "https://maxx-travel-assistant.onrender.com"

# Static fallback
CITY_TO_IATA = {
    "mumbai": "BOM", "delhi": "DEL", "dubai": "DXB", "london": "LON",
    "new york": "NYC", "paris": "PAR", "tokyo": "TYO", "bangalore": "BLR",
    "singapore": "SIN", "chicago": "CHI", "sydney": "SYD"
}

# Amadeus credentials
AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET")

# Token + cache storage
AMAD_TOKEN = {"access_token": None, "expires_at": None}
IATA_CACHE = {}  # city name -> iata

# Get new token if needed
def get_amadeus_token():
    if AMAD_TOKEN["access_token"] and AMAD_TOKEN["expires_at"] > datetime.utcnow():
        return AMAD_TOKEN["access_token"]

    resp = requests.post(
        "https://test.api.amadeus.com/v1/security/oauth2/token",
        data={
            "grant_type": "client_credentials",
            "client_id": AMADEUS_API_KEY,
            "client_secret": AMADEUS_API_SECRET
        }
    )
    resp.raise_for_status()
    token_data = resp.json()
    AMAD_TOKEN["access_token"] = token_data["access_token"]
    AMAD_TOKEN["expires_at"] = datetime.utcnow() + timedelta(seconds=token_data["expires_in"] - 30)
    return AMAD_TOKEN["access_token"]

# Dynamic IATA resolution
def resolve_city_to_iata(city: str):
    city = city.lower().strip()
    if city in IATA_CACHE:
        return IATA_CACHE[city]

    if city in CITY_TO_IATA:
        return CITY_TO_IATA[city]

    try:
        token = get_amadeus_token()
        r = requests.get(
            "https://test.api.amadeus.com/v1/reference-data/locations",
            headers={"Authorization": f"Bearer {token}"},
            params={"keyword": city, "subType": "CITY"}
        )
        if r.status_code == 200 and r.json().get("data"):
            iata_code = r.json()["data"][0]["iataCode"]
            IATA_CACHE[city] = iata_code
            return iata_code
    except:
        pass

    return None

# Extract info
def extract_info(text: str):
    text = text.lower()
    origin, destination, city, date_str = None, None, None, None

    # Flight
    flight_match = re.search(r"from ([a-z\s]+?) to ([a-z\s]+)", text)
    if flight_match:
        origin = flight_match.group(1).strip()
        destination = flight_match.group(2).strip()

    # Hotel
    hotel_match = re.search(r"(?:hotel|stay|book) in ([a-z\s]+)", text)
    if hotel_match:
        city = hotel_match.group(1).strip()

    # Date
    try:
        date = date_parser.parse(text, fuzzy=True, default=datetime.now())
        if date < datetime.now():
            date += timedelta(days=1)
        date_str = date.strftime("%Y-%m-%d")
    except:
        pass

    return origin, destination, city, date_str

@router.post("/voice/voice-webhook")
async def voice_webhook(request: Request):
    try:
        data = await request.json()
        voice_text = data.get("voice_text", "")
        user_id = data.get("user_id", "anonymous")

        if not voice_text:
            return JSONResponse(content={"response_text": "I didn't catch that. Could you please repeat?"})

        # Session memory
        if not hasattr(voice_webhook, "sessions"):
            voice_webhook.sessions = {}

        session = voice_webhook.sessions.get(user_id, {"state": "start"})
        response_text = ""

        if session["state"] == "start":
            response_text = (
                "Hi! I’m Maxx, your AI travel assistant. "
                "Say things like ‘Book flight from Mumbai to Dubai on August 15’ or "
                "‘Find hotels in Paris tomorrow’. What would you like to do?"
            )
            session["state"] = "awaiting_input"

        elif session["state"] == "awaiting_input":
            origin, destination, city, date_str = extract_info(voice_text)

            if origin and destination and date_str:
                origin_code = resolve_city_to_iata(origin)
                destination_code = resolve_city_to_iata(destination)

                if origin_code and destination_code:
                    r = requests.get(f"{BASE_URL}/booking/flights", params={
                        "origin": origin_code,
                        "destination": destination_code,
                        "date": date_str,
                        "session_id": user_id
                    })
                    if r.status_code == 200 and r.json().get("flights"):
                        flight = r.json()["flights"][0]
                        session["state"] = "flight_found"
                        session["flight"] = flight
                        response_text = (
                            f"Found a flight from {origin.title()} to {destination.title()} on {date_str}. "
                            f"Departs at {flight['departure']['at']}, airline {flight['carrier_code']}, "
                            f"₹{flight['price']['total']}. Want to book it?"
                        )
                    else:
                        response_text = "Sorry, I couldn't find any flights for that route and date."
                else:
                    response_text = "Sorry, I couldn't identify one or both cities. Please try again."

            elif city and date_str:
                city_code = resolve_city_to_iata(city)
                if city_code:
                    r = requests.get(f"{BASE_URL}/booking/hotels", params={
                        "city_code": city_code,
                        "check_in_date": date_str,
                        "check_out_date": date_str,
                        "adults": 1,
                        "session_id": user_id
                    })
                    if r.status_code == 200 and r.json().get("hotels"):
                        hotel = r.json()["hotels"][0]
                        session["state"] = "hotel_found"
                        session["hotel"] = hotel
                        response_text = (
                            f"I found a hotel in {city.title()} on {date_str}. "
                            f"{hotel['name']}, ₹{hotel['price']}. Do you want to book it?"
                        )
                    else:
                        response_text = "Sorry, no hotels found for that city and date."
                else:
                    response_text = "Sorry, I couldn’t identify the city for hotel search."

            else:
                response_text = (
                    "I didn’t understand your request fully. "
                    "Try saying 'Book flight from Delhi to Dubai on August 20'."
                )

        elif session["state"] == "flight_found":
            if "yes" in voice_text.lower():
                amount = session["flight"]["price"]
                r = requests.post(f"{BASE_URL}/booking/pay", json={
                    "amount": amount,
                    "currency": "usd",
                    "session_id": user_id
                })
                url = r.json().get("checkout_url", "")
                response_text = f"Awesome! Please complete payment here: {url}"
                session["state"] = "start"
            else:
                response_text = "Okay, let me know if you'd like to search another flight."
                session["state"] = "awaiting_input"

        elif session["state"] == "hotel_found":
            if "yes" in voice_text.lower():
                amount = session["hotel"]["price"]
                r = requests.post(f"{BASE_URL}/booking/pay", json={
                    "amount": amount,
                    "currency": "usd",
                    "session_id": user_id
                })
                url = r.json().get("checkout_url", "")
                response_text = f"Great! Complete your booking here: {url}"
                session["state"] = "start"
            else:
                response_text = "Okay, let me know if you'd like to find another hotel."
                session["state"] = "awaiting_input"

        else:
            response_text = "I'm Maxx! Say something like 'Find flights to London next week.'"

        voice_webhook.sessions[user_id] = session
        return JSONResponse(content={"response_text": response_text})

    except Exception as e:
        return JSONResponse(status_code=500, content={"response_text": f"Error: {str(e)}"})
