"""Supabase client singleton."""
from __future__ import annotations

from typing import Optional
from supabase import Client, create_client

from config import Settings

_client: Optional[Client] = None
_admin_client: Optional[Client] = None


def init_supabase_client(settings: Settings) -> None:
    """Initialize Supabase clients at startup."""
    global _client, _admin_client
    _client = create_client(settings.supabase_url, settings.supabase_anon_key)
    _admin_client = create_client(settings.supabase_url, settings.supabase_service_role_key)


def get_client() -> Client:
    """Returns the anon-level client."""
    if _client is None:
        raise RuntimeError("Supabase client not initialized. Call init_supabase_client() first.")
    return _client


def get_admin_client() -> Client:
    """Returns the service-role client (bypasses RLS - use with caution)."""
    if _admin_client is None:
        raise RuntimeError("Supabase admin client not initialized.")
    return _admin_client


def get_user_client(access_token: str) -> Client:
    """Returns a client scoped to a user's JWT (respects RLS)."""
    from config import get_settings
    settings = get_settings()
    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    client.postgrest.auth(access_token)
    return client
