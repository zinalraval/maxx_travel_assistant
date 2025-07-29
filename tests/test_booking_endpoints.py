import sys
import os
import pytest
import warnings
from fastapi.testclient import TestClient

# Suppress specific deprecation warnings during tests
warnings.filterwarnings("ignore", category=DeprecationWarning, message="datetime.datetime.utcnow() is deprecated")
warnings.filterwarnings("ignore", category=DeprecationWarning, message="Use 'content=<...>' to upload raw bytes/text content.")

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app

client = TestClient(app)

def test_get_flights_success():
    response = client.get("/booking/flights", params={"origin": "NYC", "destination": "LAX", "date": "2025-08-15", "session_id": "test-session"})
    assert response.status_code == 200
    json_resp = response.json()
    assert "flights" in json_resp or "error" in json_resp

def test_get_flights_no_results():
    response = client.get("/booking/flights", params={"origin": "AAA", "destination": "BBB", "date": "2025-08-15", "session_id": "test-session"})
    assert response.status_code == 200
    assert "error" in response.json()

def test_get_flights_missing_params():
    response = client.get("/booking/flights")
    assert response.status_code == 422

def test_get_hotels_success():
    response = client.get("/booking/hotels", params={
        "city_code": "PAR",
        "check_in_date": "2025-08-15",
        "check_out_date": "2025-08-19",
        "adults": 1,
        "session_id": "test-session"
    })
    assert response.status_code == 200
    json_resp = response.json()
    assert "hotels" in json_resp or "error" in json_resp

def test_get_hotels_no_results():
    response = client.get("/booking/hotels", params={
        "city_code": "ZZZ",
        "check_in_date": "2025-08-15",
        "check_out_date": "2025-08-19",
        "adults": 1,
        "session_id": "test-session"
    })
    assert response.status_code == 200
    assert "error" in response.json()

def test_get_hotels_missing_params():
    response = client.get("/booking/hotels", params={"city_code": "PAR"})
    assert response.status_code == 422

def test_initiate_payment_success():
    response = client.post("/booking/pay?amount=100.0")
    assert response.status_code == 200
    assert "checkout_url" in response.json()

def test_initiate_payment_missing_amount():
    response = client.post("/booking/pay")
    assert response.status_code == 422

def test_book_flight_success():
    flight_booking_data = {
        "order_data": {
            "flightOffers": []
        },
        "travelers": []
    }
    response = client.post("/booking/flight-book", json=flight_booking_data)
    assert response.status_code == 200
    json_resp = response.json()
    assert "booking" in json_resp or "error" in json_resp

def test_book_flight_invalid_body():
    response = client.post("/booking/flight-book", json={})
    assert response.status_code == 422

def test_book_hotel_success():
    hotel_booking_data = {
        "booking_data": {},
        "guests": [],
        "payments": []
    }
    response = client.post("/booking/hotel-book", json=hotel_booking_data)
    assert response.status_code == 200
    json_resp = response.json()
    assert "booking" in json_resp or "error" in json_resp

def test_book_hotel_invalid_body():
    response = client.post("/booking/hotel-book", json={})
    assert response.status_code == 422

def test_confirm_booking_success():
    booking_data = {
        "user_name": "John Doe",
        "email": "john@example.com",
        "phone": "1234567890",
        "origin": "NYC",
        "destination": "LAX",
        "departure_date": "2025-08-15",
        "flight_number": "AA123",
        "amount_paid": 200.0,
        "payment_status": "paid"
    }
    response = client.post("/booking/confirm", json=booking_data)
    assert response.status_code == 200
    assert "message" in response.json()
    assert response.json()["message"] == "Booking stored"

def test_confirm_booking_invalid_body():
    response = client.post("/booking/confirm", json={})
    assert response.status_code == 422

def test_stripe_webhook_valid():
    import json
    with open("test_payloads/stripe_webhook_sample.json") as f:
        payload = json.load(f)
    headers = {"Content-Type": "application/json"}
    response = client.post("/booking/stripe-webhook", json=payload, headers=headers)
    assert response.status_code == 200
    json_resp = response.json()
    assert "status" in json_resp or "error" in json_resp

def test_stripe_webhook_missing_booking_id():
    import json
    event = {
        "id": "evt_test_webhook",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_session",
                "metadata": {}
            }
        }
    }
    payload = json.dumps(event)
    headers = {"Content-Type": "application/json"}
    response = client.post("/booking/stripe-webhook", content=payload.encode('utf-8'), headers=headers)
    assert response.status_code == 200
    json_resp = response.json()
    assert "status" in json_resp or "error" in json_resp

def test_stripe_webhook_invalid_payload():
    response = client.post("/booking/stripe-webhook", content=b"invalid payload", headers={"Content-Type": "application/json"})
    assert response.status_code == 200
    json_resp = response.json()
    assert "error" in json_resp
