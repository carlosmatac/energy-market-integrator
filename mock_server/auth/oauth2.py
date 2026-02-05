"""
OAuth2 Authentication Module
============================
Implements OAuth2 Client Credentials Flow for API authentication.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel


# Configuration (from environment or defaults)
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "energy-trading-secret-key-change-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", "60"))

# Valid client credentials (in production, these would be in a database)
VALID_CLIENTS = {
    "energy_trading_client": "super_secret_key_2024",
}

# OAuth2 scheme for token extraction from headers
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/oauth/token")

# Router
router = APIRouter()


class Token(BaseModel):
    """OAuth2 token response model."""
    access_token: str
    token_type: str
    expires_in: int


class TokenData(BaseModel):
    """Decoded token payload."""
    client_id: str | None = None
    exp: datetime | None = None


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Payload data to encode in the token
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "iss": "energy-trading-mock-server",
    })
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_client_credentials(client_id: str, client_secret: str) -> bool:
    """
    Verify client credentials against known clients.
    
    Args:
        client_id: The client identifier
        client_secret: The client secret
        
    Returns:
        True if credentials are valid, False otherwise
    """
    if client_id not in VALID_CLIENTS:
        return False
    return VALID_CLIENTS[client_id] == client_secret


async def get_current_client(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    """
    Dependency to extract and validate the current client from JWT token.
    
    Args:
        token: The Bearer token from Authorization header
        
    Returns:
        The client_id if token is valid
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        client_id: str = payload.get("sub")
        
        if client_id is None:
            raise credentials_exception
            
        token_data = TokenData(client_id=client_id)
        
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify client still exists (in production, check database)
    if token_data.client_id not in VALID_CLIENTS:
        raise credentials_exception
        
    return token_data.client_id


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    """
    OAuth2 Client Credentials Flow - Token endpoint.
    
    Authenticate using client_id and client_secret to obtain an access token.
    
    **Request:**
    - `grant_type`: Must be "client_credentials" (or "password" for OAuth2 form compatibility)
    - `username`: The client_id
    - `password`: The client_secret
    
    **Response:**
    - `access_token`: JWT token to use in Authorization header
    - `token_type`: Always "Bearer"
    - `expires_in`: Token lifetime in seconds
    
    **Example:**
    ```bash
    curl -X POST http://localhost:8000/oauth/token \\
      -d "grant_type=client_credentials" \\
      -d "username=energy_trading_client" \\
      -d "password=super_secret_key_2024"
    ```
    """
    # Validate client credentials
    # Note: OAuth2PasswordRequestForm uses username/password fields
    # In Client Credentials flow, these map to client_id/client_secret
    if not verify_client_credentials(form_data.username, form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid client credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username},
        expires_delta=access_token_expires,
    )
    
    return Token(
        access_token=access_token,
        token_type="Bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
    )


@router.get("/token/info")
async def get_token_info(
    current_client: Annotated[str, Depends(get_current_client)]
) -> dict:
    """
    Get information about the current access token.
    
    Useful for debugging token validity.
    """
    return {
        "client_id": current_client,
        "status": "valid",
        "message": "Token is valid and active",
    }
