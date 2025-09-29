from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Project
from .serializers import ProjectSerializer
from main.tasks import run_langchain_flow # <-- Importamos la tarea
from AI.schemas.models import QueryList
from langchain_core.output_parsers import JsonOutputParser

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

    @action(detail=True, methods=['post'], url_path='run-research')
    def run_research(self, request, pk=None):
        """
        Inicia el flujo de descubrimiento de oportunidades para este proyecto.
        """
        try:
            project = self.get_object() # Obtiene el proyecto por su ID 
            
            # Preparamos los inputs para la tarea de Celery
            flow_name = "discovery_opportunities_flow"
          
            # Creamos el string formateado que espera la variable 'project_details'.
            project_details_str = (
                f"Título: {project.title}\n"
                f"Descripción: {project.description}\n"
                f"Palabras Clave: {project.keywords}"
            )
            # Reconstruimos el diccionario de inputs a la estructura que el pipeline espera.
            # El pipeline se encargará de 'format_instructions' internamente.
            parser = JsonOutputParser(pydantic_object=QueryList)
            flow_inputs = {
                "project_details": project_details_str,
                "format_instructions": parser.get_format_instructions()
            }
            
            # Encolamos la tarea, pasando el ID del proyecto
            task = run_langchain_flow.apply_async(
                args=[flow_name, flow_inputs],
                kwargs={'project_id': project.id} 
            )
            
            return Response({'status': 'Investigación iniciada', 'task_id': task.id}, status=202)
        except Project.DoesNotExist:
            return Response({'error': 'Proyecto no encontrado.'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)