from functools import lru_cache

from supabase import Client, create_client

from app.config import get_settings


class DatabaseNotConfiguredError(RuntimeError):
    """Raised when the Supabase credentials are missing."""


@lru_cache
def get_supabase() -> Client:
    """Return a process-wide Supabase client built from the environment."""
    settings = get_settings()
    if not settings.supabase_configured:
        raise DatabaseNotConfiguredError(
            "SUPABASE_URL and SUPABASE_KEY must be set."
        )
    return create_client(settings.supabase_url.strip(), settings.supabase_key.strip())


def supabase_configured() -> bool:
    """Report whether a Supabase client can be constructed. Does not call the network."""
    try:
        get_supabase()
    except DatabaseNotConfiguredError:
        return False
    return True
