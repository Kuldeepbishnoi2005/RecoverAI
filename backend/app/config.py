import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

backend_env = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(backend_env):
    load_dotenv(backend_env)
frontend_env = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", ".env")
if os.path.exists(frontend_env):
    load_dotenv(frontend_env)

DEFAULT_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImViaXZ2aGhqYm5zdHpnc3pqcXphIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODczMjY5NzAsImV4cCI6MjEwMjkwMjk3MH0.GOM0gjZAKyYYT2UBncJJmTZmfGhiO06b9s69SwguEy4"
DEFAULT_DEV_KMS_KEY = "recoverai_master_kms_key_32bytes_min_sandbox_default!"

class Settings(BaseSettings):
    PROJECT_NAME: str = "RecoverAI API Engine"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", os.getenv("APP_ENV", "development"))
    SUPABASE_URL: str = os.getenv("VITE_SUPABASE_URL", "https://ebivvhhjbnstzgszjqza.supabase.co")
    SUPABASE_KEY: str = os.getenv("VITE_SUPABASE_ANON_KEY", DEFAULT_ANON_KEY)
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
    WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "recoverai_webhook_secret_key_2026")
    RECOVERAI_KMS_KEY: str = os.getenv("RECOVERAI_KMS_KEY", DEFAULT_DEV_KMS_KEY)
    CORS_ALLOWED_ORIGINS: str = os.getenv("CORS_ALLOWED_ORIGINS", "")

    class Config:
        case_sensitive = True
        env_file = ".env"

    def get_kms_key(self) -> str:
        env = (self.ENVIRONMENT or "development").lower()
        key = self.RECOVERAI_KMS_KEY
        if env == "production":
            if not key or key == DEFAULT_DEV_KMS_KEY or len(key.strip()) == 0:
                raise RuntimeError(
                    "Production Fail-Closed Violation: RECOVERAI_KMS_KEY environment variable "
                    "must be explicitly configured with a secure master key in production mode."
                )
        return key

    def get_allowed_origins(self) -> list:
        raw = (self.CORS_ALLOWED_ORIGINS or "").strip()
        if raw:
            return [origin.strip() for origin in raw.split(",") if origin.strip()]

        env = (self.ENVIRONMENT or "development").lower()
        if env == "production":
            raise RuntimeError(
                "Production Fail-Closed Violation: CORS_ALLOWED_ORIGINS environment variable "
                "must be explicitly configured with trusted production origin(s) (e.g. Vercel frontend URL) in production mode."
            )

        return [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ]

settings = Settings()
