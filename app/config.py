import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Amadeus
    AMADEUS_CLIENT_ID = os.getenv("AMADEUS_CLIENT_ID")
    AMADEUS_CLIENT_SECRET = os.getenv("AMADEUS_CLIENT_SECRET")

    # Stripe
    STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

    # Twilio
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

    # Interakt
    INTERAKT_KEY = os.getenv("INTERAKT_KEY")
    INTERAKT_WEBHOOK_URL = os.getenv("INTERAKT_WEBHOOK_URL")
    INTERAKT_NUMBER = os.getenv("INTERAKT_NUMBER")

    # Google Calendar
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN")

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./maxx.db")

settings = Settings()
