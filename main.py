from logging.handlers import RotatingFileHandler
from fastapi import Depends, FastAPI, HTTPException, Header, Path
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse, PlainTextResponse
from routes import water_router, parcel_router, gis_router,image_router, analysis_router, stripe_router, stripe_billing_router,require_api_token
from redis import asyncio as aioredis
from utils.webdriver_pool import WebDriverPool
from db import init_db
from config import config
import logging
import sys
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('app.log', maxBytes=10000000, backupCount=5),
        logging.StreamHandler(sys.stdout)
    ]
)
logging.getLogger("botocore.credentials").setLevel(logging.WARNING)

API_KEY=config.RADCORP_API_KEY

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis = aioredis.from_url("redis://localhost:6379", encoding="utf-8", decode_responses=True)
    app.state.redis = redis
    await WebDriverPool().initialize()  # Initialize the WebDriver pool
    await init_db()
    yield
    await redis.close()
    await WebDriverPool()._close_drivers()  # Close the WebDriver pool

app = FastAPI(
    title="Land Valuation API",
    description="API for land valuation",
    version="0.1.0",    
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", summary="Health Check", description="Check if the API is running")
async def health_check():
    """
    Health check endpoint to verify if the API is running.
    Returns a simple message indicating the API status.
    """
    return {"status": "ok", "message": "API is running"}    
app.include_router(parcel_router)
app.include_router(gis_router)
app.include_router(water_router)
app.include_router(image_router) 
app.include_router(analysis_router)
app.include_router(stripe_router, prefix="/api", tags=["stripe-webhook"])
app.include_router(stripe_billing_router, prefix="/api", tags=["stripe-billing"])


# [
#   {
#     "gid": 11028,
#     "prop_id": "22499",
#     "geo_id": "R0022499",
#     "owner_name": "WOODY JACKSON D",
#     "situs_addr": "2669  ACR 182 , ,",
#     "county": "ANDERSON",
#     "acreage": null,
#     "image_url": "https://radcorp-images.s3.us-east-2.amazonaws.com/parcels/11028/aerial_11028.png"
#   }
# expose legacy name for uvicorn
main = app
