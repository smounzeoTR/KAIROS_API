import asyncio
from app.core.celery_app import celery_app
from app.services.ai_engine.optimizer import ai_optimizer

# Wrapper asynchrone car Celery est synchrone par défaut mais Gemini est async
def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

@celery_app.task(acks_late=True)
def optimize_schedule_task(google_events: list, tasks_todo: list, user_timezone: str):
    """
    Cette fonction tourne en arrière-plan dans le conteneur Worker.
    Elle n'a pas de limite de temps HTTP.
    """
    print(f"👷 WORKER: Début optimisation pour {len(tasks_todo)} tâches...")
    
    try:
        # On appelle notre service IA existant
        result = run_async(ai_optimizer.optimize_schedule(
            current_events=google_events,
            tasks_todo=tasks_todo,
            user_timezone=user_timezone
        ))
        print("✅ WORKER: Terminé !")
        return result
    except Exception as e:
        print(f"❌ WORKER ERROR: {e}")
        return {"error": str(e)}