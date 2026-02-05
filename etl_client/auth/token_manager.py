"""
Token Manager Module
====================
Handles OAuth2 token acquisition and automatic refresh.
"""

import time
import logging
from dataclasses import dataclass

import httpx

from etl_client.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class Token:
    """Represents an OAuth2 access token."""
    access_token: str
    token_type: str
    expires_in: int
    acquired_at: float
    
    @property
    def expires_at(self) -> float:
        """Calculate token expiration timestamp."""
        return self.acquired_at + self.expires_in
    
    def is_expired(self, margin_seconds: int = 300) -> bool:
        """
        Check if token is expired or will expire soon.
        
        Args:
            margin_seconds: Safety margin before actual expiration
            
        Returns:
            True if token is expired or will expire within margin
        """
        return time.time() >= (self.expires_at - margin_seconds)


class TokenManager:
    """
    Manages OAuth2 token lifecycle including acquisition and refresh.
    
    Usage:
        manager = TokenManager()
        token = await manager.get_token()
        headers = {"Authorization": f"Bearer {token}"}
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._token: Token | None = None
        self._client: httpx.AsyncClient | None = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.settings.api_base_url,
                timeout=30.0,
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    async def _acquire_token(self) -> Token:
        """
        Acquire a new OAuth2 access token.
        
        Returns:
            Token object with access token and metadata
            
        Raises:
            httpx.HTTPStatusError: If token request fails
        """
        client = await self._get_client()
        
        logger.info("Acquiring new OAuth2 token...")
        
        response = await client.post(
            "/oauth/token",
            data={
                "grant_type": "password",
                "username": self.settings.oauth_client_id,
                "password": self.settings.oauth_client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        
        response.raise_for_status()
        data = response.json()
        
        token = Token(
            access_token=data["access_token"],
            token_type=data["token_type"],
            expires_in=data["expires_in"],
            acquired_at=time.time(),
        )
        
        logger.info(
            f"Token acquired successfully. Expires in {token.expires_in} seconds."
        )
        
        return token
    
    async def get_token(self) -> str:
        """
        Get a valid access token, refreshing if necessary.
        
        This is the main method to use. It automatically handles:
        - Initial token acquisition
        - Token refresh when expired or near expiration
        
        Returns:
            Valid access token string
        """
        margin = self.settings.token_refresh_margin_seconds
        
        # Check if we need a new token
        if self._token is None or self._token.is_expired(margin):
            self._token = await self._acquire_token()
        
        return self._token.access_token
    
    async def get_auth_headers(self) -> dict[str, str]:
        """
        Get authorization headers with valid Bearer token.
        
        Returns:
            Dict with Authorization header
        """
        token = await self.get_token()
        return {"Authorization": f"Bearer {token}"}
    
    def invalidate_token(self):
        """
        Invalidate the current token.
        
        Call this if you receive a 401 response to force token refresh.
        """
        logger.warning("Token invalidated. Will refresh on next request.")
        self._token = None
