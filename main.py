from logging.handlers import RotatingFileHandler
from fastapi import Depends, FastAPI, HTTPException, Header, Path
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse, PlainTextResponse
from routes import water_router, parcel_router, gis_router,image_router, analysis_router, stripe_router, stripe_billing_router,require_api_token, catalogue_router, scrub_router, prompt_router
from utils.webdriver_pool import WebDriverPool
from services.batch import BatchService
from db import init_db
from config import config
import logging
import asyncio
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
    await WebDriverPool().initialize()  
    await init_db()
    asyncio.create_task(BatchService().recover_stuck_jobs())
    asyncio.create_task(BatchService().run_job_scheduler())  
    yield
    await WebDriverPool()._close_drivers()
app = FastAPI(
    title="Land Valuation API",
    description="API for land valuation",
    version="0.1.0",    
    lifespan=lifespan
)

origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:4173",
    "http://localhost:5173",
    "http://3.150.16.102",
    "http://3.150.16.102:80",
    "http://127.0.0.1",
    "http://127.0.0.1:3000",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
app.include_router(catalogue_router)
app.include_router(scrub_router)
app.include_router(prompt_router)
app.include_router(stripe_router, prefix="/api", tags=["stripe-webhook"])
app.include_router(stripe_billing_router, prefix="/api", tags=["stripe-billing"])

main = app
