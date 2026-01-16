from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_session
from schemas.user import SigninRequest, TokenResponse, UserResponse
from services.auth import AuthService, get_current_user
from models.user import User
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


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get Current User",
    description="Get the currently authenticated user's information"
)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information.
    
    Requires valid JWT token in Authorization header.
    
    Args:
        current_user: Current authenticated user (injected by dependency)
        
    Returns:
        UserResponse with current user information
    """
    return UserResponse.model_validate(current_user)


@router.post(
    "/verify",
    summary="Verify Token",
    description="Verify if a JWT token is valid and not expired"
)
async def verify_token(current_user: User = Depends(get_current_user)):
    """
    Verify if the provided JWT token is valid.
    
    Requires valid JWT token in Authorization header.
    
    Args:
        current_user: Current authenticated user (injected by dependency)
        
    Returns:
        Success message if token is valid
    """
    return {
        "valid": True,
        "user_id": current_user.id,
        "email": current_user.email
    }
