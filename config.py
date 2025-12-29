from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    DATABASE_URL: str = ""
    GOOGLE_MAPS_API_KEY: str = ""
    METERS_TO_FEET: float = 3.28084
    ARCGIS_STREAMS_URL: str = ""
    IMG_URL: str = ""
    RADCORP_API_KEY: str = ""
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_ID_MONTHLY: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_ACCESS_KEY_ID: str = ""
    AWS_REGION: str = ""
    DYNAMODB_TABLE_NAME: str = ""
    CHECKOUT_SUCCESS_URL: str | None = None
    CHECKOUT_CANCEL_URL: str | None = None
    PORTAL_RETURN_URL: str | None = None
    DASHBOARD_API_URL: str | None = None
    model_config = SettingsConfigDict(env_file=".env",extra='ignore')

config = Settings()