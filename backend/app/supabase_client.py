import logging

from supabase import create_client, Client
from pydantic_settings import BaseSettings
import os
from typing import Optional

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    supabase_url: str = os.getenv("SUPABASE_URL")
    supabase_key: str = os.getenv("SUPABASE_KEY")
    supabase_service_key: str = os.getenv("SUPABASE_SERVICE_KEY")
    # JWT secret for local token validation - Supabase local dev uses this well-known secret
    jwt_secret: str = os.getenv("SUPABASE_JWT_SECRET", "super-secret-jwt-token-with-at-least-32-characters-long")

    class Config:
        env_file = ".env"


settings = Settings()

# Log settings on module load
logger.info(f"=== SUPABASE CONFIG ===")
logger.info(f"SUPABASE_URL: {settings.supabase_url}")
logger.info(f"SUPABASE_KEY present: {bool(settings.supabase_key)}")
logger.info(f"SUPABASE_KEY prefix: {settings.supabase_key[:20] if settings.supabase_key else 'None'}...")
logger.info(f"SUPABASE_SERVICE_KEY present: {bool(settings.supabase_service_key)}")

# Lazy-loaded clients to avoid schema introspection on import
_supabase_client: Optional[Client] = None
_supabase_admin_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """Get Supabase client for user operations"""
    global _supabase_client
    if _supabase_client is None:
        logger.info(f"Creating Supabase client for URL: {settings.supabase_url}")
        # Create client - lazy initialization to avoid schema queries on import
        # Auth operations use the Auth API, not PostgREST, so they should work
        # even if PostgREST has schema query issues
        _supabase_client = create_client(
            settings.supabase_url,
            settings.supabase_key
        )
        logger.info("Supabase client created successfully")
    return _supabase_client


def get_supabase_admin_client() -> Client:
    """Get Supabase admin client for server-side operations"""
    global _supabase_admin_client
    if _supabase_admin_client is None:
        logger.info(f"Creating Supabase admin client for URL: {settings.supabase_url}")
        _supabase_admin_client = create_client(
            settings.supabase_url,
            settings.supabase_service_key
        )
        logger.info("Supabase admin client created successfully")
    return _supabase_admin_client


def get_supabase_client_with_token(access_token: str) -> Client:
    """Create a Supabase client with a user's access token for authenticated requests"""
    logger.debug(f"Creating Supabase client with user token for URL: {settings.supabase_url}")
    logger.debug(f"Token prefix: {access_token[:20] if access_token else 'None'}...")
    # Create a new client instance
    client = create_client(
        settings.supabase_url,
        settings.supabase_key
    )
    # Set the authorization header for PostgREST requests
    # This allows RLS policies to work correctly
    client.postgrest.auth(access_token)
    logger.debug("Supabase client with token created and auth header set")
    return client

