from typing import List
from fastapi import APIRouter, Depends, Body
from sqlmodel import Session

from app.api import deps
from app.db.session import get_db
from app.models.user import User
from app.services.calendar_service import calendar_service
from app.services.ai_engine.optimizer import ai_optimizer
from app.schemas.ai import OptimizationRequest, TaskRequest

router = APIRouter()

@router.post("/optimize")
async def optimize_day(
    request: OptimizationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Endpoint Magique : Reçoit des tâches -> Lit le Calendrier -> Renvoie le planning parfait.
    """
    # 1. Récupérer les événements réels (Google)
    # On force la récupération (même si ça prend du temps)
    try:
        google_events = await calendar_service.get_upcoming_events(user_id=current_user.id, db=db)
    except Exception:
        google_events = [] # Si pas de Google, on optimise sur une page blanche

    # 2. Lancer l'IA
    # Note: En production, cela devrait être une tâche d'arrière-plan (Celery)
    # car Gemini peut prendre 5 à 10 secondes. Pour le MVP, on attend.
    optimized_schedule = await ai_optimizer.optimize_schedule(
        current_events=google_events, 
        tasks_todo=request.tasks
    )

    return optimized_schedule