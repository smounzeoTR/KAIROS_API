from datetime import datetime
from uuid import UUID
import httpx
from fastapi import HTTPException
from sqlmodel import Session, select
from app.models.oauth import OAuthCredential
from app.core.config import settings

class GoogleCalendarService:
    
    # --- MÉTHODE INTERNE POUR RENOUVELER LE TOKEN ---
    async def _refresh_google_token(self, credential: OAuthCredential, db: Session) -> str:
        """
        Utilise le Refresh Token pour obtenir un nouvel Access Token
        et le sauvegarde en base.
        """
        if not credential.refresh_token:
            print("❌ Pas de refresh token disponible.")
            raise HTTPException(status_code=401, detail="Session expirée, veuillez vous reconnecter.")

        print("🔄 Token expiré. Tentative de renouvellement...")

        token_url = "https://oauth2.googleapis.com/token"
        payload = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "refresh_token": credential.refresh_token,
            "grant_type": "refresh_token",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=payload)
            
            if response.status_code != 200:
                print(f"❌ Échec du refresh Google: {response.text}")
                # Si le refresh échoue (ex: l'utilisateur a révoqué l'accès), on doit le déconnecter
                raise HTTPException(status_code=401, detail="Impossible de renouveler l'accès Google.")

            new_tokens = response.json()
        
        # Mise à jour en base de données
        credential.access_token = new_tokens["access_token"]
        # Parfois Google renvoie un nouveau refresh token, parfois non (on garde l'ancien)
        if new_tokens.get("refresh_token"):
            credential.refresh_token = new_tokens["refresh_token"]
        
        db.add(credential)
        db.commit()
        db.refresh(credential)
        
        print("✅ Token renouvelé avec succès !")
        return credential.access_token

    # --- LECTURE DES ÉVÉNEMENTS (Avec retry) ---
    async def get_upcoming_events(self, user_id: UUID, db: Session):
        # 1. Récupération Credentials
        statement = select(OAuthCredential).where(
            OAuthCredential.user_id == user_id,
            OAuthCredential.provider == "google"
        )
        cred = db.exec(statement).first()

        if not cred or not cred.access_token:
            raise HTTPException(status_code=401, detail="Non connecté à Google Calendar")

        # 2. Préparation requête
        url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
        now = datetime.utcnow().isoformat() + "Z"
        params = {
            "timeMin": now,
            "maxResults": 50,
            "singleEvents": True,
            "orderBy": "startTime",
        }
        
        # 3. Tentative d'appel (Boucle de retry)
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {cred.access_token}"}
            response = await client.get(url, params=params, headers=headers)

            # --- DÉTECTION DU 401 (Expiré) ---
            if response.status_code == 401:
                # On lance le refresh
                new_token = await self._refresh_google_token(cred, db)
                # On met à jour les headers avec le nouveau token
                headers = {"Authorization": f"Bearer {new_token}"}
                # On REJOUE la requête
                response = await client.get(url, params=params, headers=headers)

            # Si ça échoue encore après le refresh, c'est une vraie erreur
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Erreur Google API")

            data = response.json()

        # 4. Nettoyage des données
        clean_events = []
        for item in data.get("items", []):
            start = item.get("start", {}).get("dateTime") or item.get("start", {}).get("date")
            end = item.get("end", {}).get("dateTime") or item.get("end", {}).get("date")
            
            clean_events.append({
                "id": item.get("id"),
                "title": item.get("summary", "Sans titre"),
                "start": start,
                "end": end,
                "is_fixed": True,
                "source": "google"
            })
            
        return clean_events

    # --- CRÉATION D'ÉVÉNEMENT (Avec retry) ---
    async def create_event(self, user_id: UUID, task: dict, db: Session):
        statement = select(OAuthCredential).where(
            OAuthCredential.user_id == user_id,
            OAuthCredential.provider == "google"
        )
        cred = db.exec(statement).first()
        if not cred: return

        url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
        
        body = {
            "summary": f"⚡ {task['title']}", 
            "description": f"Généré par Kairos AI.\nRaison: {task.get('reasoning', 'Aucune')}",
            "start": {"dateTime": task['start'], "timeZone": "Europe/Paris"},
            "end": {"dateTime": task['end'], "timeZone": "Europe/Paris"}
        }

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {cred.access_token}"}
            response = await client.post(url, json=body, headers=headers)

            # --- DÉTECTION DU 401 POUR L'ÉCRITURE AUSSI ---
            if response.status_code == 401:
                new_token = await self._refresh_google_token(cred, db)
                headers = {"Authorization": f"Bearer {new_token}"}
                response = await client.post(url, json=body, headers=headers)

            if response.status_code == 200:
                print(f"✅ Google Calendar: Ajout de {task['title']}")
            else:
                print(f"❌ Erreur Google ({response.status_code}): {response.text}")

calendar_service = GoogleCalendarService()