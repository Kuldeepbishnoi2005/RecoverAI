import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables from local .env files if present
frontend_env = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", ".env")
if os.path.exists(frontend_env):
    load_dotenv(frontend_env)

DEFAULT_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImViaXZ2aGhqYm5zdHpnc3pqcXphIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODczMjY5NzAsImV4cCI6MjEwMjkwMjk3MH0.GOM0gjZAKyYYT2UBncJJmTZmfGhiO06b9s69SwguEy4"

class Settings(BaseSettings):
    PROJECT_NAME: str = "RecoverAI API Engine"
    API_V1_STR: str = "/api/v1"
    SUPABASE_URL: str = os.getenv("VITE_SUPABASE_URL", "https://ebivvhhjbnstzgszjqza.supabase.co")
    SUPABASE_KEY: str = os.getenv("VITE_SUPABASE_ANON_KEY", DEFAULT_ANON_KEY)
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
