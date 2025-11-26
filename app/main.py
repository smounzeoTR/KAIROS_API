from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Titre et description pour la documentation automatique (Swagger UI)
app = FastAPI(
    title="Kairos API",
    description="Backend intelligent pour l'assistant Kairos (FastAPI + LangChain)",
    version="1.0.0",
    docs_url="/docs", # L'URL pour tester l'API
    redoc_url="/redoc",
)

# Configuration CORS (Crucial pour que l'app mobile Flutter puisse parler à l'API)
# En prod, remplacez "*" par le domaine réel de votre app.
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    """Route de santé pour vérifier que l'API tourne."""
    return {
        "status": "online", 
        "service": "Kairos API", 
        "version": "1.0.0",
        "message": "Welcome to the Matrix of Productivity 🚀"
    }

@app.get("/health")
def health_check():
    """Utilisé par Docker/Kubernetes pour savoir si le container est vivant."""
    return {"status": "ok"}