from supabase import create_client, Client
from pydantic_settings import BaseSettings
import os
from typing import Optional


class Settings(BaseSettings):
    supabase_url: str = os.getenv("SUPABASE_URL")
    supabase_key: str = os.getenv("SUPABASE_KEY")
    supabase_service_key: str = os.getenv("SUPABASE_SERVICE_KEY")

    class Config:
        env_file = ".env"


settings = Settings()

# Lazy-loaded clients to avoid schema introspection on import
_supabase_client: Optional[Client] = None
_supabase_admin_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """Get Supabase client for user operations"""
    global _supabase_client
    if _supabase_client is None:
        # Create client - lazy initialization to avoid schema queries on import
        # Auth operations use the Auth API, not PostgREST, so they should work
        # even if PostgREST has schema query issues
        _supabase_client = create_client(
            settings.supabase_url,
            settings.supabase_key
        )
    return _supabase_client


def get_supabase_admin_client() -> Client:
    """Get Supabase admin client for server-side operations"""
    global _supabase_admin_client
    if _supabase_admin_client is None:
        _supabase_admin_client = create_client(
            settings.supabase_url,
            settings.supabase_service_key
        )
    return _supabase_admin_client


def get_supabase_client_with_token(access_token: str) -> Client:
    """Create a Supabase client with a user's access token for authenticated requests"""
    # Create a new client instance
    client = create_client(
        settings.supabase_url,
        settings.supabase_key
    )
    # Set the authorization header for PostgREST requests
    # This allows RLS policies to work correctly
    client.postgrest.auth(access_token)
    return client

