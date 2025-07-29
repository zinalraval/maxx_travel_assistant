import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Amadeus
    AMADEUS_CLIENT_ID = "SeAkqkaAfuidBZ7qD3EYOZvhFImBZbSv"
    AMADEUS_CLIENT_SECRET = "HN8yOSVg6yqD9vK9"

    # Stripe
    STRIPE_PUBLISHABLE_KEY = "pk_test_51RoLDzE8q2m1pSw43VDTXDuPaRTIPXFfCaiCiw92S0f9wm9SWBcEf0vgwK08iLprZyU0TtZ3kWwffMRfov5kTbOc00Cr7I4waH"
    STRIPE_SECRET_KEY = "sk_test_51RoLDzE8q2m1pSw49GMQeLbpBroEQLDbfOGLAKlI8NzNPWbCpwDT6Hv8FRxFmEylGUZhfOOFfJxh3uMXspdzEAl400Kghn2ZIt"
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

    # Twilio
    TWILIO_ACCOUNT_SID = "ACf75a9d16d76e0fad2a62b9405d8c306e"
    TWILIO_AUTH_TOKEN = "4fa3d6f81629e2fe4f255181b569aa51"

    # Interakt
    INTERAKT_KEY = "27914252-9124-453e-bc8d-afa12715f2b4"
    INTERAKT_WEBHOOK_URL = "http://54.241.134.87:8000/webhook/interakt-inbound"
    INTERAKT_NUMBER = "971586683206"

    # Google Calendar
    GOOGLE_CLIENT_ID = "maxx@usetripler.com"
    GOOGLE_CLIENT_SECRET = "Hinwick@2025"
    GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN")

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./maxx.db")

settings = Settings()
