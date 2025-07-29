# app/services/stripe_service.py
import stripe
from app.config import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

def create_checkout_session(amount_usd: float, currency="usd", success_url="https://example.com/success", cancel_url="https://example.com/cancel"):
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": currency,
                    "product_data": {
                        "name": "Flight Booking"
                    },
                    "unit_amount": int(amount_usd * 100),  # cents
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return session.url
    except Exception as e:
        print(f"[Stripe Error] {e}")
        return None

def handle_stripe_webhook(payload, sig_header):
    import stripe
    from app.config import settings
    stripe.api_key = settings.STRIPE_SECRET_KEY
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    # Bypass signature verification if sig_header or endpoint_secret is None (for testing only)
    if sig_header is None or endpoint_secret is None:
        import json
        event = json.loads(payload)
        return event

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
        return event
    except ValueError as e:
        # Invalid payload
        print(f"[Stripe Webhook Error] Invalid payload: {e}")
        raise e
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print(f"[Stripe Webhook Error] Invalid signature: {e}")
        raise e
