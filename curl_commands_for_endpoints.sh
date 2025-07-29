#!/bin/bash

# Base URL of the API - set explicitly for shell variable expansion
BASE_URL="http://127.0.0.1:8000"

echo "Testing GET /booking/flights"
curl -X GET "${BASE_URL}/booking/flights?origin=NYC&destination=LON&date=2025-08-15&session_id=testsession" -H "Accept: application/json"
echo -e "\n"

echo "Testing POST /booking/pay"
curl -X POST "${BASE_URL}/booking/pay" -H "Content-Type: application/json" -d '{"amount": 100.0}'
echo -e "\n"

echo "Testing GET /booking/hotels"
curl -X GET "${BASE_URL}/booking/hotels?city_code=LON&check_in_date=2025-08-15&check_out_date=2025-08-20&adults=2&session_id=testsession" -H "Accept: application/json"
echo -e "\n"

echo "Testing POST /booking/flight-book"
curl -X POST "${BASE_URL}/booking/flight-book?session_id=testsession" -H "Content-Type: application/json" -d @test_payloads/minimal_flight_booking_sample.json
echo -e "\n"

echo "Testing POST /booking/hotel-book"
curl -X POST "${BASE_URL}/booking/hotel-book?session_id=testsession" -H "Content-Type: application/json" -d @test_payloads/hotel_booking_sample.json
echo -e "\n"

echo "Testing POST /booking/confirm"
curl -X POST "${BASE_URL}/booking/confirm" -H "Content-Type: application/json" -d @test_payloads/flight_booking_sample.json
echo -e "\n"

echo "Testing POST /booking/stripe-webhook"
curl -X POST "${BASE_URL}/booking/stripe-webhook" -H "Content-Type: application/json" -H "stripe-signature: test_signature" -d @test_payloads/stripe_webhook_sample.json
echo -e "\n"

echo "Testing POST /voice/voice-webhook"
curl -X POST "${BASE_URL}/voice/voice-webhook" -H "Content-Type: application/json" -d '{"voice_text": "Book flight from Mumbai to Dubai on August 15", "user_id": "testuser"}'
echo -e "\n"
