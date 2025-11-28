import json
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from app.core.config import settings
from app.schemas.ai import ScheduledItem, TaskRequest, OptimizedSchedule

class AIOptimizer:
    def __init__(self):
        # Initialisation de Gemini Pro
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.1, # Faible température = plus rigoureux/logique
            convert_system_message_to_human=True,
            transport="rest"
        )
        
        # Le Parser force Gemini à répondre en JSON strict compatible avec notre Schema
        self.parser = PydanticOutputParser(pydantic_object=OptimizedSchedule)

    async def optimize_schedule(self, current_events: List[dict], tasks_todo: List[TaskRequest], user_timezone: str = "UTC"):
        # --- LOGIQUE DYNAMIQUE ---
        try:
            # On essaie d'utiliser le fuseau envoyé par le mobile
            print("Zone Info = {user_timezone}")
            user_tz = ZoneInfo(user_timezone)
        except Exception:
            # Si le téléphone envoie n'importe quoi, on fallback sur UTC
            print(f"⚠️ Fuseau inconnu '{user_timezone}', fallback sur UTC")
            user_tz = ZoneInfo("UTC")

        # On prépare le contexte temporel
        now = datetime.now().isoformat()
        # On calcule 'Maintenant' pour CET utilisateur spécifique
        now_local = datetime.now(user_tz)
        now_str = now_local.strftime("%Y-%m-%d %H:%M")
        
        # LE PROMPT (L'instruction magique)
        template = """
        Tu es un assistant expert (ton nom est KAIROS) en gestion du temps (Time Management).
        Ton objectif est d'insérer une liste de tâches dans un agenda existant sans créer de conflits.

        CONTEXTE ACTUEL :
        HEURE ACTUELLE : {now} (Ne planifie RIEN avant cette heure précise pour aujourd'hui).

        DONNÉES D'ENTRÉE :
        1. Agenda existant (FIXE) : {events}
        2. Tâches à insérer (FLEXIBLES) : {tasks}
        
        RÈGLES D'OR :
        1. CRITIQUE : Aucune tâche ne doit commencer dans le passé (avant l'heure actuelle).
        2. Si une tâche a un 'preferred_time' :
           - Essaie de la placer à cette heure-là ou juste après.
           - Si l'heure est déjà passée aujourd'hui, planifie-la pour DEMAIN à cette heure.
        3. Si pas de 'preferred_time', trouve le meilleur trou libre.
        4. Les événements 'google' sont fixes.

        RÈGLES STRICTES :
        1. Ne modifie jamais l'heure des événements fixes.
        2. Trouve les trous (gaps) entre les événements fixes pour y insérer les tâches.
        3. Si une tâche est trop longue pour un trou, tu peux ne pas la planifier (mais essaie de tout caser).
        4. Ne planifie rien la nuit (entre 23h et 07h) sauf si nécessaire.
        5. Ajoute une petite explication courte dans le champ "reasoning" pour chaque tâche ajoutée (ex: "Inséré après le déjeuner").

        FORMAT DE SORTIE ATTENDU :
        Tu dois répondre UNIQUEMENT avec un objet JSON. Cet objet doit contenir une clé "schedule" qui est une liste d'objets.
        Chaque objet dans la liste "schedule" doit avoir : title, start (ISO8601), end (ISO8601), type ("event" ou "task"), reasoning.
        Inclue les événements originaux ET les nouvelles tâches dans la liste "schedule" finale.
        
        {format_instructions}
        """

        prompt = PromptTemplate(
            template=template,
            input_variables=["now", "events", "tasks"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )

        # Création de la chaîne
        chain = prompt | self.llm | self.parser

        # Exécution
        try:
            print("🧠 IA : Préparation des données...")
            
            # On convertit simplement les listes de dictionnaires en texte JSON string
            events_str = json.dumps(current_events, default=str)
            tasks_str = json.dumps(tasks_todo, default=str)
            print("🧠 IA : Réflexion en cours...")
            result = await chain.ainvoke({
                "now": now_str,
                "timezone": user_timezone,
                "events": events_str, #json.dumps(current_events, default=str), # On convertit les objets en string
                "tasks": tasks_str #[t.dict() for t in tasks_todo]
            })
            
            return result.schedule

        except Exception as e:
            print(f"❌ Erreur IA : {str(e)}")
            # En cas d'erreur, on renvoie juste l'agenda original sans modif
            return current_events

ai_optimizer = AIOptimizer()