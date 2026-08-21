from supabase import create_client, Client
from app.config import settings

def get_supabase_client() -> Client:
    """Returns initialized Supabase Client."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

def get_supabase_admin_client() -> Client:
    """Returns admin Supabase client with service role key for backend operations."""
    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_KEY
    return create_client(settings.SUPABASE_URL, key)
