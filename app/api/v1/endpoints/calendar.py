from typing import Any, List
from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api import deps  # Notre fichier de sécurité
from app.db.session import get_db
from app.models.user import User
from app.services.calendar_service import calendar_service

router = APIRouter()

@router.get("/events")
async def read_events(
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user) # <--- SÉCURITÉ ICI
) -> List[Any]:
    """
    Récupère les événements du calendrier Google de l'utilisateur connecté.
    """
    events = await calendar_service.get_upcoming_events(user_id=current_user.id, db=db)
    return events