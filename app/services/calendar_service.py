from datetime import datetime
from uuid import UUID
import httpx
from fastapi import HTTPException
from sqlmodel import Session, select
from app.models.oauth import OAuthCredential

class GoogleCalendarService:
    async def get_upcoming_events(self, user_id: UUID, db: Session):
        # 1. Récupérer le token Google de l'utilisateur
        statement = select(OAuthCredential).where(
            OAuthCredential.user_id == user_id,
            OAuthCredential.provider == "google"
        )
        cred = db.exec(statement).first()

        if not cred or not cred.access_token:
            raise HTTPException(status_code=401, detail="Utilisateur non connecté à Google Calendar")

        # 2. Préparer la requête vers Google
        # On veut les événements à partir de maintenant
        now = datetime.utcnow().isoformat() + "Z"  # 'Z' indique UTC
        
        url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
        params = {
            "timeMin": now,
            "maxResults": 20,       # On limite à 20 pour commencer
            "singleEvents": True,   # Découpe les événements récurrents en instances individuelles
            "orderBy": "startTime",
        }
        headers = {
            "Authorization": f"Bearer {cred.access_token}"
        }

        # 3. Appel API via HTTPX (Asynchrone)
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, headers=headers)
            
            if response.status_code == 401:
                # TODO: Ici, il faudra implémenter le "Refresh Token" si le token est expiré.
                # Pour l'instant, on renvoie une erreur demandant de se reconnecter.
                raise HTTPException(status_code=401, detail="Token Google expiré, veuillez vous reconnecter")
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Erreur Google API")

            data = response.json()

        # 4. Nettoyage et simplification des données
        # On transforme le format complexe de Google en un format simple pour notre app mobile
        clean_events = []
        for item in data.get("items", []):
            # Google gère les dates soit en 'dateTime' (RDV précis), soit en 'date' (Journée entière)
            start = item.get("start", {}).get("dateTime") or item.get("start", {}).get("date")
            end = item.get("end", {}).get("dateTime") or item.get("end", {}).get("date")
            
            clean_events.append({
                "id": item.get("id"),
                "title": item.get("summary", "Sans titre"),
                "start": start,
                "end": end,
                "is_fixed": True, # C'est un RDV Google, donc considéré comme fixe dans Kairos
                "source": "google"
            })
            
        return clean_events

    async def create_event(self, user_id: UUID, task: dict, db: Session):
        """Crée un événement unique dans Google Calendar"""
        # 1. Récup token (copier la logique de get_upcoming_events ou factoriser)
        statement = select(OAuthCredential).where(
            OAuthCredential.user_id == user_id,
            OAuthCredential.provider == "google"
        )
        cred = db.exec(statement).first()
        if not cred: return None # Ou lever erreur

        url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
        headers = {"Authorization": f"Bearer {cred.access_token}"}
        
        # 2. Corps de la requête Google
        body = {
            "summary": f"⚡ {task['title']}", # On ajoute un emoji pour distinguer les tâches Kairos
            "description": f"Planifié par Kairos AI.\nRaisonnement: {task.get('reasoning', '')}",
            "start": {"dateTime": task['start'], "timeZone": "Europe/Paris"}, # Adapter TZ si besoin
            "end": {"dateTime": task['end'], "timeZone": "Europe/Paris"}
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=body, headers=headers)
            if resp.status_code == 200:
                print(f"✅ Créé dans Google: {task['title']}")
                return resp.json()
            else:
                print(f"❌ Erreur Création Google: {resp.text}")
                return None
# Instance unique du service
calendar_service = GoogleCalendarService()