# from celery import Celery
# from .config import settings
# from celery.schedules import crontab

# # Initialize Celery
# celery_app = Celery(
#     "ticketing_worker",
#     # Use the centralized settings object for broker and backend URLs
#     broker=settings.redis_url,
#     backend=settings.redis_url, # Stores the result of the task here
#     include=['app.tasks']
# )

# # Optional configuration: make tasks acknowledge they succeeded before removing them from the queue
# celery_app.set_default()
# celery_app.conf.update(task_acks_late=True)
# celery_app.conf.timezone = "UTC"