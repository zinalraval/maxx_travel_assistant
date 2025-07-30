from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import os
import re
import requests
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from app.config import settings

router = APIRouter()

CITY_TO_IATA = {
    "mumbai": "BOM", "delhi": "DEL", "dubai": "DXB",
    "london": "LON", "new york": "NYC", "paris": "PAR",
    "tokyo": "TYO", "bangalore": "BLR", "singapore": "SIN",
    "chicago": "CHI", "sydney": "SYD"
}

BASE_URL = "https://maxx-travel-assistant.onrender.com"

AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET")

AMAD_TOKEN = {"access_token": None, "expires_at": None}
IATA_CACHE = {}

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
            params={"keyword": city, "subType": "CITY,AIRPORT"}
        )
        if r.status_code == 200 and r.json().get("data"):
            for location in r.json()["data"]:
                if location.get("iataCode") and location.get("subType") in ["CITY", "AIRPORT"]:
                    iata_code = location["iataCode"]
                    IATA_CACHE[city] = iata_code
                    return iata_code
    except Exception as e:
        print(f"Error resolving city to IATA: {e}")

    return None

def extract_info(text: str):
    text = text.lower()
    origin, destination, city, date_str = None, None, None, None

    # Enhanced regex patterns for more natural language
    flight_patterns = [
        r"from ([a-z\s]+?(?:airport)?) to ([a-z\s]+?(?:airport)?)",
        r"flying from ([a-z\s]+) to ([a-z\s]+)",
        r"flight from ([a-z\s]+) to ([a-z\s]+)",
        r"book.*flight.*from ([a-z\s]+) to ([a-z\s]+)",
        r"need.*flight.*from ([a-z\s]+) to ([a-z\s]+)",
        r"want.*flight.*from ([a-z\s]+) to ([a-z\s]+)",
        r"([a-z\s]+) to ([a-z\s]+)",  # Simple "A to B" pattern
    ]
    
    for pattern in flight_patterns:
        flight_match = re.search(pattern, text)
        if flight_match:
            origin = flight_match.group(1).replace("airport", "").strip()
            destination = flight_match.group(2).replace("airport", "").strip()
            print(f"🔍 [DEBUG] Flight pattern matched: '{pattern}' -> origin='{origin}', destination='{destination}'")
            break

    # Enhanced hotel patterns
    hotel_patterns = [
        r"(?:hotel|stay|book|need|want).*in ([a-z\s]+)",
        r"(?:hotel|stay|book|need|want).*at ([a-z\s]+)",
        r"([a-z\s]+).*hotel",
    ]
    
    for pattern in hotel_patterns:
        hotel_match = re.search(pattern, text)
        if hotel_match:
            city = hotel_match.group(1).strip()
            print(f"🔍 [DEBUG] Hotel pattern matched: '{pattern}' -> city='{city}'")
            break

    # Enhanced date parsing with multiple formats
    date_patterns = [
        r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})",  # DD/MM/YYYY or MM/DD/YYYY
        r"(\d{4})-(\d{1,2})-(\d{1,2})",  # YYYY-MM-DD
        r"(\w+)\s+(\d{1,2})",  # Month Day (e.g., "August 15")
        r"(\d{1,2})\s+(\w+)",  # Day Month (e.g., "15 August")
        r"tomorrow",
        r"today",
        r"next\s+(\w+)",  # next week, next month
    ]
    
    for pattern in date_patterns:
        date_match = re.search(pattern, text)
        if date_match:
            try:
                if pattern == r"tomorrow":
                    date = datetime.now() + timedelta(days=1)
                elif pattern == r"today":
                    date = datetime.now()
                elif pattern == r"next\s+(\w+)":
                    # Handle "next week", "next month" etc.
                    period = date_match.group(1)
                    if period == "week":
                        date = datetime.now() + timedelta(weeks=1)
                    elif period == "month":
                        # Approximate next month
                        date = datetime.now() + timedelta(days=30)
                    else:
                        date = date_parser.parse(text, fuzzy=True, default=datetime.now())
                else:
                    date = date_parser.parse(text, fuzzy=True, default=datetime.now())
                
                if date < datetime.now():
                    date += timedelta(days=1)
                date_str = date.strftime("%Y-%m-%d")
                print(f"🔍 [DEBUG] Date pattern matched: '{pattern}' -> date='{date_str}'")
                break
            except:
                continue
    
    # If no date found, try fuzzy parsing
    if not date_str:
        try:
            date = date_parser.parse(text, fuzzy=True, default=datetime.now())
            if date < datetime.now():
                date += timedelta(days=1)
            date_str = date.strftime("%Y-%m-%d")
            print(f"🔍 [DEBUG] Fuzzy date parsing -> date='{date_str}'")
        except:
            date_str = None

    return origin, destination, city, date_str

@router.post("/voice/voice-webhook")
async def voice_webhook(request: Request):
    try:
        data = await request.json()
        
        # Log the full incoming payload for debugging
        print(f"🔍 [DEBUG] Full Millis payload: {data}")
        
        # Handle different possible field names from Millis
        voice_text = data.get("voice_text") or data.get("message") or data.get("text", "")
        user_id = data.get("user_id") or data.get("session_id", "anonymous")
        
        # Check for structured metadata from Millis LLM tools
        metadata = data.get("metadata", {})
        if metadata:
            print(f"🔍 [DEBUG] Millis metadata found: {metadata}")
            # Use Millis-extracted entities if available
            origin = metadata.get("origin")
            destination = metadata.get("destination") 
            date_str = metadata.get("date") or metadata.get("departure_date")
            adults = metadata.get("adults", 1)
            
            if origin and destination and date_str:
                print(f"🔍 [DEBUG] Using Millis extracted entities: origin={origin}, destination={destination}, date={date_str}")
                # Skip regex extraction and use Millis data directly
                origin_code = resolve_city_to_iata(origin)
                destination_code = resolve_city_to_iata(destination)
                
                if not origin_code:
                    return JSONResponse(content={"response_text": f"I couldn't find a match for '{origin}'. Please try again with a nearby city."})
                if not destination_code:
                    return JSONResponse(content={"response_text": f"I couldn't find a match for '{destination}'. Please try again with a nearby city."})
                
                # Call flight search API
                r = requests.get(f"{BASE_URL}/booking/flights", params={
                    "origin": origin_code,
                    "destination": destination_code,
                    "date": date_str,
                    "session_id": user_id
                })
                
                print(f"🔍 [DEBUG] Flight search response status: {r.status_code}")
                if r.status_code == 200 and r.json().get("flights"):
                    flight = r.json()["flights"][0]
                    response_text = (
                        f"Great! I found a flight from {origin.title()} to {destination.title()} on {date_str}. "
                        f"It departs at {flight.get('departure', {}).get('at', 'TBD')} with {flight.get('carrier_code', 'TBD')}, "
                        f"and costs ₹{flight.get('price', {}).get('total', 'TBD')}. Shall I book it for you?"
                    )
                    return JSONResponse(content={"response_text": response_text})
                else:
                    response_text = "Sorry, no flights found for that route and date."
                    return JSONResponse(content={"response_text": response_text})

        # Fallback to regex extraction if no metadata
        print(f"🔍 [DEBUG] No Millis metadata, using regex extraction on: '{voice_text}'")
        
        if not voice_text:
            return JSONResponse(content={"response_text": "I didn't catch that. Could you say it again?"})

        if not hasattr(voice_webhook, "sessions"):
            voice_webhook.sessions = {}

        session = voice_webhook.sessions.get(user_id, {"state": "start"})
        response_text = ""

        origin, destination, city, date_str = extract_info(voice_text)
        
        print(f"🔍 [DEBUG] Regex extracted: origin='{origin}', destination='{destination}', city='{city}', date='{date_str}'")

        def unknown_city_msg(city_name):
            return f"I couldn't find a match for '{city_name}'. Please try again with a nearby city."

        if origin and destination and date_str:
            origin_code = resolve_city_to_iata(origin)
            destination_code = resolve_city_to_iata(destination)
            
            print(f"🔍 [DEBUG] IATA codes: origin='{origin_code}', destination='{destination_code}'")

            if not origin_code:
                return JSONResponse(content={"response_text": unknown_city_msg(origin)})
            if not destination_code:
                return JSONResponse(content={"response_text": unknown_city_msg(destination)})

            r = requests.get(f"{BASE_URL}/booking/flights", params={
                "origin": origin_code,
                "destination": destination_code,
                "date": date_str,
                "session_id": user_id
            })
            
            print(f"🔍 [DEBUG] Flight search API call: status={r.status_code}, response={r.text[:200]}")
            
            if r.status_code == 200 and r.json().get("flights"):
                flight = r.json()["flights"][0]
                session.update({
                    "state": "flight_found",
                    "flight": flight
                })
                response_text = (
                    f"Great! I found a flight from {origin.title()} to {destination.title()} on {date_str}. "
                    f"It departs at {flight.get('departure', {}).get('at', 'TBD')} with {flight.get('carrier_code', 'TBD')}, "
                    f"and costs ₹{flight.get('price', {}).get('total', 'TBD')}. Shall I book it for you?"
                )
                voice_webhook.sessions[user_id] = session
                return JSONResponse(content={"response_text": response_text})
            else:
                response_text = "Sorry, no flights found for that route and date."
        elif origin and destination and not date_str:
            response_text = "Got your cities. Please tell me the date you'd like to travel."
            session.update({"origin": origin, "destination": destination, "state": "awaiting_date"})

        elif city and date_str:
            city_code = resolve_city_to_iata(city)
            if not city_code:
                return JSONResponse(content={"response_text": unknown_city_msg(city)})

            r = requests.get(f"{BASE_URL}/booking/hotels", params={
                "city_code": city_code,
                "check_in_date": date_str,
                "check_out_date": date_str,
                "adults": 1,
                "session_id": user_id
            })
            if r.status_code == 200 and r.json().get("hotels"):
                hotel = r.json()["hotels"][0]
                session.update({
                    "state": "hotel_found",
                    "hotel": hotel
                })
                response_text = (
                    f"I found a hotel in {city.title()} on {date_str}. "
                    f"{hotel.get('name', 'Hotel')}, ₹{hotel.get('price', 'TBD')}. Do you want to book it?"
                )
                voice_webhook.sessions[user_id] = session
                return JSONResponse(content={"response_text": response_text})
            else:
                response_text = "Sorry, no hotels found for that city and date."

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
            # Enhanced fallback message with specific guidance
            response_text = (
                "I didn't catch all the details. Could you please tell me:\n"
                "• Where you're flying from\n"
                "• Where you're flying to\n"
                "• When you want to travel\n\n"
                "For example: 'Book me a flight from Mumbai to London on August 15'"
            )
            session["state"] = "awaiting_input"

        voice_webhook.sessions[user_id] = session
        return JSONResponse(content={"response_text": response_text})

    except Exception as e:
        print(f"❌ [ERROR] Voice webhook error: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"response_text": f"Sorry, there was an error: {str(e)}"})
