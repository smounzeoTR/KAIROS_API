from fastapi import APIRouter, Request, Depends, HTTPException
from starlette.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from sqlmodel import Session, select
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.models.oauth import OAuthCredential
from app.core.security import create_access_token
from urllib.parse import quote

router = APIRouter()

oauth = OAuth()
oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile https://www.googleapis.com/auth/calendar'
    }
)

@router.get("/login")
async def login(request: Request):
    #redirect_uri = request.url_for('auth_callback')
    redirect_uri = f"{settings.BASE_URL}/api/v1/auth/callback"
    # access_type=offline est CRUCIAL pour obtenir le Refresh Token (accès en arrière-plan)
    return await oauth.google.authorize_redirect(request, redirect_uri, access_type='offline', prompt='consent')

@router.get("/callback", name="auth_callback")
async def auth_callback(request: Request, db: Session = Depends(get_db)):
    try:
        # 1. Échange du code contre les tokens
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        email = user_info.get('email')

        if not email:
            raise HTTPException(status_code=400, detail="Email non fourni par Google")

        # 2. Recherche si l'utilisateur existe déjà
        statement = select(User).where(User.email == email)
        user = db.exec(statement).first()

        # 3. Si non, on le crée
        if not user:
            user = User(
                email=email,
                full_name=user_info.get('name'),
                hashed_password="", # Pas de mot de passe car OAuth
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # 4. Sauvegarde / Mise à jour des Tokens Google (Pour l'IA)
        # On cherche si on a déjà des crédentials pour ce user
        cred_statement = select(OAuthCredential).where(
            OAuthCredential.user_id == user.id, 
            OAuthCredential.provider == "google"
        )
        credential = db.exec(cred_statement).first()

        if not credential:
            credential = OAuthCredential(user_id=user.id, provider="google", access_token="")

        # Mise à jour des tokens
        credential.access_token = token.get('access_token')
        # Google ne renvoie le refresh_token que la première fois (ou avec prompt='consent')
        if token.get('refresh_token'):
            credential.refresh_token = token.get('refresh_token')
        
        credential.expires_at = token.get('expires_at')
        
        db.add(credential)
        db.commit()

        # 5. Création du Token de Session (JWT) pour l'App Mobile
        access_token = create_access_token(subject=user.id)
        safe_name = quote(user.full_name)

        # On passe le token en paramètre d'URL
        mobile_redirect_url = f"kairos://callback?token={access_token}&name={safe_name}"
        
        return RedirectResponse(url=mobile_redirect_url)

    except Exception as e:
        # En cas d'erreur, on redirige vers l'app avec un message d'erreur
        return RedirectResponse(url=f"kairos://callback?error={str(e)}")