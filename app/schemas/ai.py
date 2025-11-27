from typing import List, Optional
from pydantic import BaseModel

# Ce que le mobile envoie pour demander une optimisation
class TaskRequest(BaseModel):
    title: str
    duration_minutes: int
    priority: str = "medium" # low, medium, high

class OptimizationRequest(BaseModel):
    tasks: List[TaskRequest]

# Ce que l'IA renvoie (un créneau planifié)
class ScheduledItem(BaseModel):
    title: str
    start: str  # ISO 8601
    end: str    # ISO 8601
    type: str   # "event" (Google) ou "task" (IA)
    reasoning: Optional[str] = None # Pourquoi l'IA a mis ça là