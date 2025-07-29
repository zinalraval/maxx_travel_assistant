from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import re
import requests
from datetime import datetime
from dateutil import parser as date_parser

router = APIRouter()

CITY_TO_IATA = {
    "mumbai": "BOM", "delhi": "DEL", "dubai": "DXB",
    "london": "LON", "new york": "NYC", "paris": "PAR",
    "tokyo": "TYO", "bangalore": "BLR", "singapore": "SIN",
    "chicago": "CHI", "sydney": "SYD"
}

BASE_URL = "https://maxx-travel-assistant.onrender.com"  

def extract_info(text):
    text = text.lower()
    origin, destination, date_str, city_code = None, None, None, None

    flight_match = re.search(r"from ([a-zA-Z\s]+?) to ([a-zA-Z\s]+)", text)
    if flight_match:
        origin = flight_match.group(1).strip()
        destination = flight_match.group(2).strip()

    hotel_match = re.search(r"(?:hotels?|stay) in ([a-zA-Z\s]+)", text)
    if hotel_match:
        city_code = hotel_match.group(1).strip()

    for keyword in ["today", "tomorrow", "next", "on"]:
        if keyword in text:
            try:
                parsed_date = date_parser.parse(text, fuzzy=True, default=datetime.now())
                date_str = parsed_date.strftime("%Y-%m-%d")
                break
            except:
                pass

    return origin, destination, date_str, city_code

@router.post("/voice-webhook")
async def voice_webhook(request: Request):
    try:
        data = await request.json()
        voice_text = data.get("voice_text", "")
        user_id = data.get("user_id", "default")

        if not hasattr(voice_webhook, "sessions"):
            voice_webhook.sessions = {}

        session = voice_webhook.sessions.get(user_id, {"state": "start"})
        response_text = ""

        if not voice_text:
            return JSONResponse(content={"response_text": "I didn't hear anything. Please repeat."})

        if session["state"] == "start":
            response_text = (
                "Hi! I’m Maxx, your AI travel assistant. "
                "You can say things like ‘Book flight from Mumbai to Dubai on August 15’ or "
                "‘Find hotels in Paris from August 10 to 15’. What would you like to do?"
            )
            session["state"] = "awaiting_info"

        elif session["state"] == "awaiting_info":
            origin, destination, date_str, city_code = extract_info(voice_text)

            # Flight intent
            if origin and destination and date_str:
                origin_iata = CITY_TO_IATA.get(origin.lower())
                destination_iata = CITY_TO_IATA.get(destination.lower())

                if origin_iata and destination_iata:
                    flight_url = f"{BASE_URL}/booking/flights"
                    r = requests.get(flight_url, params={"origin": origin_iata, "destination": destination_iata, "date": date_str, "session_id": user_id})
                    if r.status_code == 200 and r.json().get("flights"):
                        flight = r.json()["flights"][0]
                        session["state"] = "flight_found"
                        session["flight_data"] = flight
                        response_text = (
                            f"Found a flight from {origin.title()} to {destination.title()} on {date_str}. "
                            f"Departure at {flight['departure']['at']} with {flight['carrier_code']} "
                            f"for ₹{flight['price']['total']}. Want to book it?"
                        )
                    else:
                        response_text = "Sorry, I couldn't find any flights for that route and date."

                else:
                    response_text = "Sorry, I only support popular cities like Mumbai, Dubai, London, and New York."

            # Hotel intent
            elif city_code and date_str:
                iata_city = CITY_TO_IATA.get(city_code.lower())
                if iata_city:
                    hotel_url = f"{BASE_URL}/booking/hotels"
                    r = requests.get(hotel_url, params={
                        "city_code": iata_city,
                        "check_in_date": date_str,
                        "check_out_date": date_str,
                        "adults": 1,
                        "session_id": user_id
                    })
                    if r.status_code == 200 and r.json().get("hotels"):
                        hotel = r.json()["hotels"][0]
                        session["state"] = "hotel_found"
                        session["hotel_data"] = hotel
                        response_text = (
                            f"I found a hotel in {city_code.title()} for {date_str}. "
                            f"{hotel['name']}, priced at ₹{hotel['price']}. Want to book it?"
                        )
                    else:
                        response_text = "No hotels found for that city and date."
                else:
                    response_text = "Sorry, hotel search is only available in major cities."

            else:
                response_text = "Please say your travel plan clearly. For example, 'Book flight from Delhi to Dubai on August 20'."

        elif session["state"] == "flight_found":
            if "yes" in voice_text.lower():
                # Start payment process
                r = requests.post(f"{BASE_URL}/booking/pay", json={"amount": session["flight_data"]["price"], "currency": "usd", "session_id": user_id})
                payment_url = r.json().get("checkout_url", "https://example.com/pay")
                response_text = f"Great! Please complete your payment here: {payment_url}"
                session["state"] = "start"
            else:
                response_text = "Got it! Let me know if you'd like to search another flight."
                session["state"] = "awaiting_info"

        elif session["state"] == "hotel_found":
            if "yes" in voice_text.lower():
                r = requests.post(f"{BASE_URL}/booking/pay", json={"amount": session["hotel_data"]["price"], "currency": "usd", "session_id": user_id})
                payment_url = r.json().get("checkout_url", "https://example.com/pay")
                response_text = f"Awesome! Complete your booking by paying here: {payment_url}"
                session["state"] = "start"
            else:
                response_text = "Okay. Let me know if you want to find another hotel."
                session["state"] = "awaiting_info"

        else:
            response_text = "I'm here to help you book travel. Say something like 'Book a hotel in Paris next week'."

        voice_webhook.sessions[user_id] = session
        return JSONResponse(content={"response_text": response_text})

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
