from datetime import datetime, timedelta
from typing import Any, Union
from jose import jwt
from app.core.config import settings

ALGORITHM = "HS256"

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    """Génère un JWT signé avec notre SECRET_KEY."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Par défaut, le token est valide 7 jours
        expire = datetime.utcnow() + timedelta(days=7)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt