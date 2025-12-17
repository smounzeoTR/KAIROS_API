from typing import Optional
from sqlmodel import Field, SQLModel
from datetime import datetime, timezone
from enum import Enum

class EmailTaskStatus(str, Enum):
    PENDING = "pending"   # En attente de validation par l'utilisateur
    CONVERTED = "converted" # Validé et transformé en vraie tâche
    IGNORED = "ignored"   # Rejeté par l'utilisateur

class EmailTask(SQLModel, table=True):
    __tablename__ = "email_tasks"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)  # Pour savoir à qui appartient le mail
    
    # Infos techniques Gmail (pour le Deep Link et éviter les doublons)
    gmail_id: str = Field(unique=True, index=True) 
    email_sender: str
    email_subject: str
    
    # L'analyse de Gemini
    ai_title: str
    ai_duration: int
    ai_priority: int
    ai_summary: str
    ai_reason: Optional[str] = None

    # État du traitement
    status: EmailTaskStatus = Field(default=EmailTaskStatus.PENDING)
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))