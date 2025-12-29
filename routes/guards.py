from fastapi import Header, HTTPException
from config import config
def require_api_token(authorization: str | None = Header(default=None)):
    expected = config.RADCORP_API_KEY
    if not expected:
        raise HTTPException(status_code=500, detail="Server misconfiguration: missing RADCORP_API_KEY")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    if token != expected:
        raise HTTPException(status_code=403, detail="Invalid API key")
