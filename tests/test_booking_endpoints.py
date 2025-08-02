import pytest
from fastapi.testclient import TestClient
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app

client = TestClient(app)

def test_flight_search_valid():
    response = client.get("/booking/flights", params={
        "originLocationCode": "NYC",
        "destinationLocationCode": "LON",
        "departureDate": "2024-11-01",
        "adults": 1,
        "children": 1,
        "session_id": "testsession"
    })
    assert response.status_code == 200
    assert "flights" in response.json()

def test_flight_inspiration():
    response = client.get("/booking/flight-inspiration", params={"origin": "NYC"})
    assert response.status_code == 200
    assert "flight_inspiration" in response.json()

def test_flight_cheapest_date():
    response = client.get("/booking/flight-cheapest-date", params={"origin": "NYC", "destination": "LON"})
    assert response.status_code == 200
    assert "flight_cheapest_date" in response.json()

def test_flight_upselling():
    body = {"some": "data"}
    response = client.post("/booking/flight-upselling", json=body)
    assert response.status_code == 200
    assert response.json() is not None

def test_flight_seatmap_get():
    response = client.get("/booking/flight-seatmap", params={"flight_order_id": "123"})
    assert response.status_code == 200
    assert response.json() is not None

def test_flight_seatmap_post():
    body = {"some": "data"}
    response = client.post("/booking/flight-seatmap", json=body)
    assert response.status_code == 200
    assert response.json() is not None

def test_trip_purpose_prediction():
    params = {
        "origin": "NYC",
        "destination": "LON",
        "departure_date": "2024-11-01",
        "return_date": "2024-11-10"
    }
    response = client.get("/booking/trip-purpose-prediction", params=params)
    assert response.status_code == 200
    assert response.json() is not None

def test_transfer_search():
    body = {"some": "data"}
    response = client.post("/booking/transfer-search", json=body)
    assert response.status_code == 200
    assert response.json() is not None

def test_transfer_booking():
    body = {"some": "data"}
    response = client.post("/booking/transfer-booking", json=body, params={"offer_id": "offer123"})
    assert response.status_code == 200
    assert response.json() is not None

def test_flight_search_invalid_date():
    response = client.get("/booking/flights", params={
        "originLocationCode": "NYC",
        "destinationLocationCode": "LON",
        "departureDate": "invalid-date",
        "session_id": "testsession"
    })
    assert response.status_code == 400

def test_hotel_search_valid():
    response = client.get("/booking/hotels", params={
        "city_code": "LON",
        "check_in_date": "2024-11-01",
        "check_out_date": "2024-11-05",
        "adults": 1,
        "session_id": "testsession"
    })
    assert response.status_code == 200
    assert "hotels" in response.json()

def test_flight_booking():
    flight_booking_data = {
        "order_data": {"flightOffers": []},
        "travelers": [{"id": "1", "name": "Test User"}]
    }
    response = client.post("/booking/flight-book", json=flight_booking_data, params={"session_id": "testsession"})
    assert response.status_code == 200
    assert "booking" in response.json()

def test_hotel_booking():
    hotel_booking_data = {
        "booking_data": {},
        "guests": [{"id": "1", "name": "Test User"}],
        "payments": []
    }
    response = client.post("/booking/hotel-book", json=hotel_booking_data, params={"session_id": "testsession"})
    assert response.status_code == 200
    assert "booking" in response.json()

def test_payment_initiation():
    response = client.post("/booking/pay", json={"amount": 100.0})
    assert response.status_code == 200
    assert "checkout_url" in response.json()

def test_booking_confirmation():
    booking_data = {
        "user_name": "Test User",
        "email": "test@example.com",
        "phone": "1234567890"
    }
    response = client.post("/booking/confirm", json=booking_data)
    assert response.status_code == 200
    assert "booking_id" in response.json()

def test_voice_webhook():
    voice_data = {
        "text": "Book flight from New York to London on November 1",
        "session_id": "testsession"
    }
    response = client.post("/voice/voice-webhook", json=voice_data)
    assert response.status_code == 200
    assert "response_text" in response.json()
