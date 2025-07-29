# app/main.py
from fastapi import FastAPI
from app.routes import voice, booking

app = FastAPI(
    title="MAXX Travel Agent",
    version="1.0.0",
    description="Voice-based flight and hotel booking assistant"
)

# Mount routes
app.include_router(voice.router, prefix="/voice", tags=["Voice Agent"])
app.include_router(booking.router, prefix="/booking", tags=["Booking"])

@app.get("/")
def root():
    return {"message": "MAXX Travel Agent is running"}
