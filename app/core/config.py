from typing import Optional
from pydantic import PostgresDsn, field_validator, ValidationInfo
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Kairos API"
    SECRET_KEY: str = ""
    BASE_URL: str
    
    # Configuration PostgreSQL par défaut (correspond au docker-compose)
    POSTGRES_SERVER: str = "db"
    POSTGRES_USER: str = "kairos_admin"
    POSTGRES_PASSWORD: str = "kairos_secure_pass"
    POSTGRES_DB: str = "kairos_db"
    
    # URL de connexion complète (sera construite automatiquement)
    DATABASE_URL: Optional[str] = None

    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    # Gemini key
    GOOGLE_API_KEY: str

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info: ValidationInfo) -> str:
        if isinstance(v, str):
            return v
        
        # On construit l'URL : postgresql://user:pass@server/db
        return str(PostgresDsn.build(
            scheme="postgresql",
            username=info.data.get("POSTGRES_USER"),
            password=info.data.get("POSTGRES_PASSWORD"),
            host=info.data.get("POSTGRES_SERVER"),
            path=f"{info.data.get('POSTGRES_DB') or ''}",
        ))

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()