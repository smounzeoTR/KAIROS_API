from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlmodel import SQLModel

from app.core.config import settings
from app.db.session import engine

# IMPORTANT : On doit importer les modèles ici pour que SQLModel les "voie"
# et puisse créer les tables au démarrage.
from app.models.user import User 

from app.api.v1.endpoints import auth

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Fonction exécutée au démarrage (avant le yield) 
    et à l'arrêt (après le yield) de l'application.
    """
    print("🚀 Démarrage de Kairos API...")
    print("🛠️ Vérification des tables de base de données...")
    SQLModel.metadata.create_all(engine)
    print("✅ Tables synchronisées.")
    yield
    print("🛑 Arrêt de Kairos API.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Middleware Session (Obligatoire pour Authlib)
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# Configuration CORS
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusion des routes
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])

@app.get("/")
def read_root():
    return {"status": "online", "message": "Kairos API is running with DB connection 🚀"}

@app.get("/health")
def health_check():
    return {"status": "ok"}