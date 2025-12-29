import os, stripe
from fastapi import APIRouter, Request, HTTPException
from config import config
router = APIRouter()

stripe.api_key = config.STRIPE_SECRET_KEY
WEBHOOK_SECRET = config.STRIPE_WEBHOOK_SECRET  # set from Stripe Dashboard
@router.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    """
    Stripe POSTs events here. We verify with the signing secret and handle events.
    IMPORTANT: Use the RAW request body for verification (using request.body()).
    """
    if not WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Missing STRIPE_WEBHOOK_SECRET")

    payload = await request.body()  # raw bytes
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload, sig_header=sig_header, secret=WEBHOOK_SECRET
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook verification failed: {e}")

    etype = event["type"]
    data = event["data"]["object"]

    # --- Handle the events you selected in the Dashboard ---
    if etype == "checkout.session.completed":
        # session = data
        # TODO: look up/create your user, persist customer/subscription IDs, mark active, etc.
        pass

    elif etype == "invoice.paid":
        # pi/invoice was paid; keep membership active
        pass

    elif etype == "invoice.payment_failed":
        # notify user / mark past-due in your system
        pass

    elif etype == "customer.subscription.created":
        # sub = data
        pass

    elif etype == "customer.subscription.updated":
        # sub = data
        pass

    elif etype == "customer.subscription.deleted":
        # sub canceled; mark membership inactive
        pass

    elif etype == "customer.subscription.paused":
        # mark membership paused
        pass

    elif etype == "customer.subscription.resumed":
        # mark membership active again
        pass

    # -------------------------------------------------------

    return {"received": True}
