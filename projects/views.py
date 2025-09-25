# projects/views.py
from rest_framework import viewsets, permissions
from .models import Project
from .serializers import ProjectSerializer

class ProjectViewSet(viewsets.ModelViewSet):
    """
    API endpoint que permite a los usuarios ver o editar sus propios proyectos.
    """
    serializer_class = ProjectSerializer
    # Permiso: Solo los usuarios autenticados pueden acceder.
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Esta vista solo debe devolver los proyectos del usuario actualmente autenticado.
        """
        return Project.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        """
        Asigna automáticamente el proyecto al usuario que lo está creando.
        """
        serializer.save(user=self.request.user)