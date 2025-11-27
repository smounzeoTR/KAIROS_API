from typing import Optional
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, AutoString
from pydantic import EmailStr

class User(SQLModel, table=True):
    __tablename__ = "users"  # Nom explicite de la table dans Postgres

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    email: EmailStr = Field(unique=True, index=True, sa_type=AutoString)
    hashed_password: str
    
    full_name: Optional[str] = None
    
    # Gestion des abonnements (FREE, PRO, FOUNDER)
    subscription_tier: str = Field(default="FREE")
    
    is_active: bool = Field(default=True)