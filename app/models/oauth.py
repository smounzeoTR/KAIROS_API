from uuid import UUID
from sqlmodel import Field, SQLModel, AutoString

class OAuthCredential(SQLModel, table=True):
    __tablename__ = "oauth_credentials"

    id: int = Field(default=None, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id")
    
    provider: str = Field(index=True)  # ex: "google"
    
    # On stocke les tokens en texte brut pour l'instant (MVP).
    # En prod, il faudrait les chiffrer.
    access_token: str = Field(sa_type=AutoString)
    refresh_token: str | None = Field(default=None, sa_type=AutoString)
    
    expires_at: int | None = None  # Timestamp d'expiration