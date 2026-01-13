from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_session
from schemas.user import SigninRequest, TokenResponse, UserResponse
from services.auth import AuthService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post(
    "/signin",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User Signin",
    description="Authenticate a user with email and password, returns JWT access token"
)
async def signin(
    credentials: SigninRequest,
    db: AsyncSession = Depends(get_session)
):
    """
    Authenticate user and return JWT access token.
    
    Args:
        credentials: User email and password
        db: Database session
        
    Returns:
        TokenResponse with access token and user information
        
    Raises:
        HTTPException: 401 if authentication fails
    """
    # Authenticate user
    user = await AuthService.authenticate_user(
        db=db,
        email=credentials.email,
        password=credentials.password
    )
    
    if not user:
        # Generic error message to prevent user enumeration
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = AuthService.create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email
        }
    )
    
    # Return token and user info
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )
