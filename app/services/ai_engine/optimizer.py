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
            print(f"Zone Info = {user_timezone}")
            user_tz = ZoneInfo(user_timezone)
        except Exception:
            print(f"⚠️ Fuseau inconnu '{user_timezone}', fallback sur UTC")
            user_tz = ZoneInfo("UTC")

        # On calcule 'Maintenant' pour CET utilisateur spécifique et on le formate en ISO 8601
        # Ce format (ex: 2024-07-23T21:00:00+02:00) est non-ambigu et contient le fuseau horaire.
        now_local = datetime.now(user_tz).isoformat()
        
        # LE PROMPT (L'instruction magique)
        template = """
        Tu es un assistant expert (ton nom est KAIROS) en gestion du temps (Time Management).
        Ton objectif est d'insérer une liste de tâches dans un agenda existant sans créer de conflits.

        CONTEXTE TEMPOREL :
        - Fuseau horaire de l'utilisateur : {timezone}
        - Heure actuelle de l'utilisateur : {now} (Ne planifie RIEN avant cette heure précise pour aujourd'hui).

        DONNÉES D'ENTRÉE :
        1. Agenda existant (ÉVÉNEMENTS FIXES) : {events}
        2. Tâches à insérer (FLEXIBLES) : {tasks}
        
        RÈGLES D'OR :
        1. CRITIQUE : Aucune tâche ne doit commencer dans le passé (avant l'heure actuelle).
        2. RÈGLE IMPÉRATIVE POUR 'preferred_time' :
           Si une tâche a une heure préférée (ex: "14:00") :
           - CAS A : Le créneau de 14:00 est LIBRE ? -> Tu DOIS planifier la tâche à 14:00:00 précises. Pas 14:05, pas 13:55.
           - NOTE IMPORTANTE : La valeur de 'preferred_time' est une heure locale dans le fuseau de l'utilisateur ({timezone}). Ne la traite PAS comme de l'UTC.
           - CAS B : Le créneau est DÉJÀ PRIS par un événement ? -> Alors, et seulement alors, cherche le prochain créneau libre juste après.
           - CAS C : L'heure préférée est DÉJÀ PASSÉE par rapport à l'heure actuelle ({now}) ? -> Planifie-la au prochain créneau disponible.
        3. Tâches sans heure préférée :
           - Insère-les intelligemment dans les créneaux libres restants.
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
            input_variables=["now", "events", "tasks", "timezone"],
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
                "now": now_local,
                "timezone": user_timezone,
                "events": events_str, #json.dumps(current_events, default=str), # On convertit les objets en string
                "tasks": tasks_str #[t.dict() for t in tasks_todo]
            })
            print (f"Résultat : {result}")
            return result.schedule

        except Exception as e:
            print(f"❌ Erreur IA : {str(e)}")
            # En cas d'erreur, on renvoie juste l'agenda original sans modif
            return current_events

ai_optimizer = AIOptimizer()