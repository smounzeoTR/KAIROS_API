import os.path
import base64
import json
import re
import google.generativeai as genai
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from app.core.config import settings

# --- CONFIGURATION ---
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

genai.configure(api_key=settings.GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash-lite')

# --- FONCTIONS UTILITAIRES ---

def clean_text(text):
    """Nettoie le HTML et les espaces inutiles"""
    # Enlève les balises HTML basiques
    text = re.sub('<[^<]+?>', '', text) 
    # Enlève les sauts de ligne multiples
    return " ".join(text.split())

def get_email_body(payload):
    """Extrait le corps du message de manière récursive (Texte ou HTML)"""
    body = ""
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body'].get('data')
                if data:
                    body += base64.urlsafe_b64decode(data).decode('utf-8')
            elif part['mimeType'] == 'multipart/alternative':
                body += get_email_body(part)
    elif 'body' in payload and 'data' in payload['body']:
        data = payload['body']['data']
        body += base64.urlsafe_b64decode(data).decode('utf-8')
    
    return clean_text(body)

def analyze_with_gemini(sender, subject, body):
    # Prompt renforcé pour mieux détecter les urgences
    prompt = f"""
    Tu es un assistant exécutif. Analyse cet email.
    
    CONTEXTE :
    De: {sender}
    Sujet: {subject}
    Contenu: {body[:1500]}

    TA MISSION :
    Détermine si cet email demande une ACTION concrète de ma part (Tâche).
    
    RÉPONSE JSON STRICTE :
    {{
        "is_task": true/false,
        "title": "Titre Action (Verbe + Sujet, max 5 mots)",
        "duration_minutes": nombre_entier (ex: 15),
        "priority": 1_a_5 (5 = Urgent/Immédiat),
        "reason": "Pourquoi tu penses que c'est une tâche ?"
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(text)
    except Exception as e:
        print(f"⚠️ Erreur Gemini : {e}")
        return {"is_task": False}

# --- MAIN ---

def main():
    creds = None
    if os.path.exists("token.json"):
        try:
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        except Exception:
            print("⚠️ Token corrompu, on le recrée.")
            creds = None
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None # Force la reconnexion si le refresh échoue
        
        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            # ICI LE FIX CRUCIAL : on force le 'consent' pour avoir le refresh_token
            creds = flow.run_local_server(port=8080, access_type='offline', prompt='consent')
        
        # On sauvegarde le nouveau token propre
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    service = build("gmail", "v1", credentials=creds)

    # J'ai enlevé 'is:unread' pour vos tests.
    # Comme ça, même si vous avez ouvert le mail, le script le verra.
    query = "is:unread -category:primary -category:promotions -category:notifications"
    
    print(f"🔍 Scan (5 derniers mails reçus)...")
    results = service.users().messages().list(userId="me", q=query, maxResults=5).execute()
    messages = results.get("messages", [])

    if not messages:
        print("✅ Aucun mail trouvé.")
        return

    for message in messages:
        msg = service.users().messages().get(userId="me", id=message["id"], format="full").execute()
        headers = msg["payload"]["headers"]
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "Sans sujet")
        sender = next((h["value"] for h in headers if h["name"] == "From"), "Inconnu")
        
        body = get_email_body(msg['payload'])
        
        # DEBUG : Affiche ce que Gemini va vraiment lire
        # Si c'est vide ici, c'est que l'extraction a échoué
        print(f"\n📧 SUJET : {subject}")
        # print(f"DEBUG BODY : {body[:50]}...") 

        analysis = analyze_with_gemini(sender, subject, body)

        if analysis.get("is_task"):
            print(f"   🔥 TÂCHE DÉTECTÉE (Priorité {analysis['priority']}/5)")
            print(f"   👉 {analysis['title']} ({analysis['duration_minutes']} min)")
            print(f"   💡 Raison : {analysis.get('reason')}")
        else:
            print(f"   💤 Pas d'action (Info/Pub)")

if __name__ == "__main__":
    main()