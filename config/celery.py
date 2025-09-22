# django_celery_project/celery.py
import os
from celery import Celery

# Establece el módulo de configuración de Django para el programa 'celery'.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('django_celery_project')

# Usa strings aquí para que el worker no tenga que serializar
# el objeto de configuración a los procesos hijos.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Carga automáticamente los módulos de tareas de todas las aplicaciones registradas.
app.autodiscover_tasks()