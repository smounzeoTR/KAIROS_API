from sqlmodel import create_engine, Session
from app.core.config import settings

# Création du moteur de connexion
# echo=True permet de voir les requêtes SQL dans le terminal (utile pour le debug)
engine = create_engine(settings.DATABASE_URL, echo=True)

def get_db():
    """
    Fonction de dépendance (Dependency Injection).
    Crée une session DB pour une requête, et la ferme après.
    """
    with Session(engine) as session:
        yield session