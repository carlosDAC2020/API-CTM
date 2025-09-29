
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProjectViewSet

# Creamos un router y registramos nuestro viewset con él.
router = DefaultRouter()
router.register(r'', ProjectViewSet, basename='project')
app_name = "projects"

# Las URLs de la API son ahora determinadas automáticamente por el router.
urlpatterns = [
    path('', include(router.urls)),
]