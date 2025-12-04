from typing import List
from fastapi import APIRouter, Depends, Body
from sqlmodel import Session

from app.api import deps
from app.db.session import get_db
from app.models.user import User
from app.services.calendar_service import calendar_service
from app.services.ai_engine.optimizer import ai_optimizer
from app.schemas.ai import OptimizationRequest
from app.workers.ai_task import optimize_schedule_task

router = APIRouter()

@router.post("/optimize")
async def optimize_day(
    request: OptimizationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    print(f"📥 Reçu de Flutter: {len(request.tasks)} tâches à optimiser")
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
    tasks_for_ai = [t.dict() for t in request.tasks]
    # Note: En production, cela devrait être une tâche d'arrière-plan (Celery)
    task = optimize_schedule_task.delay(
        google_events=google_events,
        tasks_todo=tasks_for_ai,
        user_timezone=request.user_timezone
    )

    # On retourne juste l'ID du ticket
    return {"task_id": task.id, "status": "processing"}

# 2. Endpoint pour VÉRIFIER le statut
@router.get("/optimize/status/{task_id}")
async def get_optimization_status(task_id: str):
    task_result = AsyncResult(task_id)
    
    if task_result.state == 'PENDING':
        return {"status": "processing"}
    elif task_result.state == 'SUCCESS':
        return {"status": "completed", "result": task_result.result}
    elif task_result.state == 'FAILURE':
        return {"status": "failed", "error": str(task_result.result)}
    
    return {"status": task_result.state}