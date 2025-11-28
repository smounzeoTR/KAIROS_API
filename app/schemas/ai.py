from typing import List, Optional
from pydantic import BaseModel

# Ce que le mobile envoie pour demander une optimisation
class TaskRequest(BaseModel):
    title: str
    duration: int
    priority: int # 1=low, 2=medium, 3=high
    preferred_time: Optional[str] = None

class OptimizationRequest(BaseModel):
    tasks: List[TaskRequest]
    user_timezone: str = "UTC"

# Ce que l'IA renvoie (un créneau planifié)
class ScheduledItem(BaseModel):
    title: str
    start: str  # ISO 8601
    end: str    # ISO 8601
    type: str   # "event" (Google) ou "task" (IA)
    reasoning: Optional[str] = None # Pourquoi l'IA a mis ça là

# Le modèle qui encapsule la liste de sortie de l'IA
class OptimizedSchedule(BaseModel):
    schedule: List[ScheduledItem]