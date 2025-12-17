from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List

from app.api import deps
from app.models.user import User
from app.models.mail import EmailTask, EmailTaskStatus
from app.services.email_service import EmailService

router = APIRouter()

@router.post("/scan")
def trigger_email_scan(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Lance l'analyse des emails via Gemini.
    """
    service = EmailService(user_id=current_user.id, db=db)
    result = service.scan_and_process_emails()
    return result

@router.get("/pending", response_model=List[EmailTask])
def get_pending_email_tasks(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Récupère toutes les tâches issues d'emails en attente de validation.
    """
    statement = select(EmailTask).where(
        EmailTask.user_id == current_user.id,
        EmailTask.status == EmailTaskStatus.PENDING
    )
    return db.exec(statement).all()