from typing import Any, List
from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api import deps  # Notre fichier de sécurité
from app.db.session import get_db
from app.models.user import User
from app.services.calendar_service import calendar_service
from app.schemas.ai import ScheduledItem

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

@router.post("/sync")
async def sync_calendar(
    tasks: List[ScheduledItem], # On reçoit la liste validée par l'user
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Prend les tâches validées et les pousse dans Google"""
    count = 0
    for item in tasks:
        # On ne ré-écrit pas les événements qui viennent déjà de Google !
        if item.type == 'task': 
            # On convertit l'objet Pydantic en dict pour le service
            await calendar_service.create_event(current_user.id, item.dict(), db)
            count += 1
    
    return {"status": "success", "created": count}