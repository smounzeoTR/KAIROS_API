from fastapi import APIRouter, Request, Depends
from authlib.integrations.starlette_client import OAuth
from starlette.responses import RedirectResponse
from app.core.config import settings

router = APIRouter()

# Configuration Authlib
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
    """Redirige l'utilisateur vers la page de connexion Google."""
    redirect_uri = request.url_for('auth_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/callback", name="auth_callback")
async def auth_callback(request: Request):
    """Google renvoie l'utilisateur ici après la connexion."""
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        
        # Pour l'instant, on affiche juste les infos pour prouver que ça marche.
        # Plus tard, on créera l'utilisateur en base ici.
        return {
            "status": "success",
            "email": user_info.get("email"),
            "name": user_info.get("name"),
            "google_token": "Token reçu avec succès (caché pour sécurité)"
        }
    except Exception as e:
        return {"error": str(e)}