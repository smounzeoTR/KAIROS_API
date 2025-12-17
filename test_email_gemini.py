import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Si on modifie ces scopes, il faut supprimer le fichier token.json
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def main():
    creds = None
    # Le fichier token.json stocke les tokens d'accès et de refresh.
    # Il est créé automatiquement lors de la première connexion.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    
    # Si pas d'identifiants valides, on lance le flow de connexion
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # On utilise le fichier credentials.json que vous avez téléchargé
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=8080)
        
        # On sauvegarde le token pour la prochaine fois
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        # Connexion au service Gmail
        service = build("gmail", "v1", credentials=creds)

        # REQUÊTE INTELLIGENTE :
        # - is:unread : Seulement les non lus
        # - category:primary : Uniquement la boîte principale
        # - -category:promotions : Pas de pubs
        # - -category:social : Pas de Facebook/LinkedIn
        query = "is:unread category:primary "#-category:promotions -category:social"
        
        print(f"🔍 Recherche des mails avec le filtre : '{query}'...")
        
        results = service.users().messages().list(userId="me", q=query, maxResults=10).execute()
        messages = results.get("messages", [])

        if not messages:
            print("✅ Aucun mail non lu trouvé (Inbox Zero !).")
            return

        print(f"📬 {len(messages)} mails trouvés :\n")
        
        for message in messages:
            # Récupération des détails (Snippet + Headers)
            msg = service.users().messages().get(userId="me", id=message["id"], format="full").execute()
            
            headers = msg["payload"]["headers"]
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "Sans sujet")
            sender = next((h["value"] for h in headers if h["name"] == "From"), "Inconnu")
            snippet = msg.get("snippet", "")

            print(f"📧 De : {sender}")
            print(f"   Sujet : {subject}")
            print(f"   Aperçu : {snippet[:100]}...")
            print("-" * 50)

    except Exception as error:
        print(f"❌ Une erreur est survenue : {error}")

if __name__ == "__main__":
    main()