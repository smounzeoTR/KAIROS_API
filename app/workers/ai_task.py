import asyncio
from app.core.celery_app import celery_app
from app.services.ai_engine.optimizer import ai_optimizer

@celery_app.task(acks_late=True, time_limit=300) # Ajout d'un timeout de 5 minutes
def optimize_schedule_task(google_events: list, tasks_todo: list, user_timezone: str):
    """
    Cette fonction tourne en arrière-plan dans le conteneur Worker.
    Elle n'a pas de limite de temps HTTP.
    """
    print(f"👷 WORKER: Début optimisation pour {len(tasks_todo)} tâches...")
    
    try:
        # On appelle notre service IA existant
        # asyncio.run() est la méthode standard et robuste pour exécuter une coroutine
        # depuis un contexte synchrone comme une tâche Celery.
        result = asyncio.run(ai_optimizer.optimize_schedule(
            current_events=google_events,
            tasks_todo=tasks_todo,
            user_timezone=user_timezone
        ))
        
        if isinstance(result, list):
            # Check if items are Pydantic models before calling .dict()
            # (LangChain sometimes returns dicts directly, sometimes objects)
            serializable_result = []
            for item in result:
                if hasattr(item, 'dict'):
                    serializable_result.append(item.dict())
                else:
                    serializable_result.append(item)
            
            print("✅ WORKER: Terminé! Données sous format JSON.")
            return serializable_result
        
        print("✅ WORKER: Terminé !")
        return result
    except Exception as e:
        print(f"❌ WORKER ERROR: {e}")
        # Il est préférable de lever l'exception pour que Celery marque la tâche comme 'FAILURE'
        raise
