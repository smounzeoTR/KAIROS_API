from typing import Generator, Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlmodel import Session

from app.core.config import settings
from app.core.security import ALGORITHM
from app.db.session import get_db
from app.models.user import User

# C'est l'URL que FastAPI utilisera pour la doc Swagger si on veut se loguer (optionnel ici)
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.BASE_URL}/api/v1/auth/login"
)

def get_current_user(
    token: Annotated[str, Depends(reusable_oauth2)],
    db: Annotated[Session, Depends(get_db)]
) -> User:
    """
    Cette fonction est le 'Videur'. 
    Elle est appelée avant chaque route protégée.
    1. Elle récupère le token.
    2. Elle le décrypte.
    3. Elle cherche l'utilisateur en base.
    4. Si tout est OK, elle retourne l'objet User. Sinon, elle jette une erreur 401.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide: ID utilisateur manquant",
            )
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
        )

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Utilisateur introuvable"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Utilisateur inactif"
        )
        
    return user