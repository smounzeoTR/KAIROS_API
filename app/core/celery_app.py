from celery import Celery
import os

# On lit l'URL Redis depuis l'env ou on met une valeur par défaut pour Docker
redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "kairos_worker",
    broker=redis_url,
    backend=redis_url,
    include=['app.workers.ai_task']
)

#celery_app.conf.task_routes = {
#   "app.workers.ai_task.optimize_schedule_task": "main-queue"
#}