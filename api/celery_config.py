import os
from celery import Celery

# Configuration de Redis
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = os.getenv("REDIS_PORT", "6381")

# Configuration de Celery
celery_app = Celery(
    "scraper",
    broker=f"redis://{redis_host}:{redis_port}/0",
    backend=f"redis://{redis_host}:{redis_port}/0",
    include=['api.tasks']  # Import tasks
)