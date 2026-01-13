from fastapi import APIRouter, Depends, HTTPException
import stripe
from .guards import require_api_token
from config import config
from models import CheckoutIn, PropertyInfo, PortalIn
router = APIRouter()

# Required env vars
STRIPE_SECRET_KEY = config.STRIPE_SECRET_KEY
if not STRIPE_SECRET_KEY:
    raise RuntimeError("STRIPE_SECRET_KEY not set")
stripe.api_key = STRIPE_SECRET_KEY

PRICE_ID_MONTHLY = config.STRIPE_PRICE_ID_MONTHLY
if not PRICE_ID_MONTHLY:
    raise RuntimeError("STRIPE_PRICE_ID_MONTHLY not set")

# Optional: customize where Stripe Checkout returns after success/cancel
SUCCESS_URL = config.CHECKOUT_SUCCESS_URL or "https://https://api.texasparcels.com/docs#/Search/trigger_analysis_search_trigger_analysis_post"
CANCEL_URL  = config.CHECKOUT_CANCEL_URL  or "https://https://api.texasparcels.com/docs#/default/health_check_health_get"
PORTAL_RETURN_URL = config.PORTAL_RETURN_URL or "https://https://api.texasparcels.com/docs#/"



@router.post("/checkout-session")
def create_checkout_session(payload: CheckoutIn, _=Depends(require_api_token)):
    """
    Creates a Stripe Checkout Session for $60 per property selected.
    Returns a hosted `url` to redirect the browser, and the `id` if you prefer Stripe.js redirect.
    """
    try:
        quantity = len(payload.properties)
        # Store property info as a string for metadata
        property_metadata = ";".join([f"{p.propertyId}:{p.county}" for p in payload.properties])
        params: dict = {
            "mode": "subscription",
            "success_url": SUCCESS_URL,
            "cancel_url": CANCEL_URL,
            "line_items": [{
                "price": PRICE_ID_MONTHLY,
                "quantity": quantity
            }],
            "allow_promotion_codes": payload.allowPromoCodes,
            "metadata": {
                "userId": payload.userId or "",
                "properties": property_metadata
            },
            "subscription_data": {
                "metadata": {
                    "userId": payload.userId or "",
                    "properties": property_metadata
                }
            },
        }

        # Provide either a customer (preferred if you store it) or an email for Checkout to create one
        if payload.customerId:
            params["customer"] = payload.customerId
        else:
            params["customer_email"] = payload.email

        session = stripe.checkout.Session.create(**params)
        return {"url": session["url"], "id": session["id"]}
    except stripe.StripeError as e:
        msg = getattr(e, "user_message", None) or str(e)
        raise HTTPException(status_code=400, detail=msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/portal-session")
def create_portal_session(payload: PortalIn, _=Depends(require_api_token)):
    """
    Creates a Billing Portal session so users can manage/cancel their subscription.
    """
    try:
        portal = stripe.billing_portal.Session.create(
            customer=payload.customerId,
            return_url=PORTAL_RETURN_URL
        )
        return {"url": portal["url"]}
    except stripe.StripeError as e:
        msg = getattr(e, "user_message", None) or str(e)
        raise HTTPException(status_code=400, detail=msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
