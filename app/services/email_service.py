import os
import json
import base64
import re
from typing import List
import google.generativeai as genai
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlmodel import Session, select

from app.core.config import settings 
from app.models.mail import EmailTask, EmailTaskStatus

# Configuration Gemini
genai.configure(api_key=settings.GOOGLE_API_KEY) 
model = genai.GenerativeModel('gemini-2.5-flash')

class EmailService:
    
    def __init__(self, user_id: int, db: Session):
        self.user_id = user_id
        self.db = db
        self.creds = self._get_credentials()

    def _get_credentials(self):
        """
        Récupère les crédentials. 
        TODO V2: Récupérer depuis la DB (models/oauth.py) pour l'utilisateur connecté.
        Pour l'instant: Utilise le fichier local token.json.
        """
        token_path = "/app/token.json" 
        if os.path.exists(token_path):
            return Credentials.from_authorized_user_file(token_path, ["https://www.googleapis.com/auth/gmail.readonly"])
        return None

    def _clean_text(self, text: str) -> str:
        text = re.sub('<[^<]+?>', '', text) 
        return " ".join(text.split())

    def _get_email_body(self, payload) -> str:
        body = ""
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data')
                    if data:
                        body += base64.urlsafe_b64decode(data).decode('utf-8')
                elif part['mimeType'] == 'multipart/alternative':
                    body += self._get_email_body(part)
        elif 'body' in payload and 'data' in payload['body']:
            data = payload['body']['data']
            body += base64.urlsafe_b64decode(data).decode('utf-8')
        return self._clean_text(body)

    def _analyze_with_gemini(self, sender, subject, body):
        prompt = f"""
        Tu es un assistant exécutif. Analyse cet email.
        De: {sender}, Sujet: {subject}, Contenu: {body[:1500]}
        Détermine si cet email demande une ACTION concrète.
        RÉPONSE JSON STRICTE :
        {{
            "is_task": true/false,
            "title": "Verbe + Sujet (max 5 mots)",
            "duration_minutes": entier,
            "priority": 1_a_5,
            "summary": "Résumé en 1 phrase",
            "reason": "Pourquoi c'est une tâche"
        }}
        """
        try:
            response = model.generate_content(prompt)
            text = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(text)
        except Exception as e:
            print(f"Erreur Gemini: {e}")
            return {"is_task": False}

    def scan_and_process_emails(self):
        """Scan les mails et sauvegarde les tâches en DB"""
        if not self.creds or not self.creds.valid:
            print("❌ Pas de crédentials valides. Authentifiez-vous d'abord.")
            return {"status": "error", "message": "No valid token found"}

        service = build("gmail", "v1", credentials=self.creds)
        
        # Filtre: Non lu + Notifications ou Personnel        
        query = "is:unread -category:primary -category:promotions -category:notifications"
        
        results = service.users().messages().list(userId="me", q=query, maxResults=10).execute()
        messages = results.get("messages", [])
        
        tasks_created = 0

        for message in messages:
            # Vérifier si on a déjà traité ce mail (éviter doublons)
            existing = self.db.exec(select(EmailTask).where(EmailTask.gmail_id == message["id"])).first()
            if existing:
                continue

            msg = service.users().messages().get(userId="me", id=message["id"], format="full").execute()
            headers = msg["payload"]["headers"]
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "Sans sujet")
            sender = next((h["value"] for h in headers if h["name"] == "From"), "Inconnu")
            body = self._get_email_body(msg['payload'])

            analysis = self._analyze_with_gemini(sender, subject, body)

            if analysis.get("is_task"):
                new_task = EmailTask(
                    user_id=self.user_id,
                    gmail_id=message["id"],
                    email_sender=sender,
                    email_subject=subject,
                    ai_title=analysis.get("title", "Tâche sans titre"),
                    ai_duration=analysis.get("duration_minutes", 15),
                    ai_priority=analysis.get("priority", 1),
                    ai_summary=analysis.get("summary", ""),
                    ai_reason=analysis.get("reason", ""),
                    status=EmailTaskStatus.PENDING
                )
                self.db.add(new_task)
                tasks_created += 1
        
        self.db.commit()
        return {"status": "success", "tasks_found": tasks_created}