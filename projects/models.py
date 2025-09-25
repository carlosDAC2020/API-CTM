from django.db import models
from django.contrib.auth.models import User # Usamos el User de Django por defecto

class Project(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    title = models.CharField(max_length=255)
    description = models.TextField()
    keywords = models.JSONField(default=list, help_text="Una lista de palabras clave, ej: ['IA', 'salud']")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
class Research(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pendiente'),
        ('RUNNING', 'En Ejecución'),
        ('COMPLETED', 'Completado'),
        ('FAILED', 'Fallido'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='researches')
    execute_time = models.FloatField(null=True, blank=True, help_text="Tiempo total de ejecución en segundos")
    date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')

    # --- CAMPOS PARA LAS MÉTRICAS ---
    initial_results_count = models.PositiveIntegerField(default=0, help_text="Número total de resultados de búsqueda iniciales (web + RSS)")
    relevant_results_count = models.PositiveIntegerField(default=0, help_text="Número de resultados considerados relevantes por el escrutinador")
    opportunities_found_count = models.PositiveIntegerField(default=0, help_text="Número final de oportunidades extraídas")

    @property
    def relevance_ratio(self):
        """Métrica 1: resultados inciales vs relevantes"""
        if self.initial_results_count == 0:
            return 0.0
        return (self.relevant_results_count / self.initial_results_count) * 100

    @property
    def opportunity_ratio(self):
        """Métrica 2: de los relevantes, cuántos generaron oportunidades"""
        if self.relevant_results_count == 0:
            return 0.0
        return (self.opportunities_found_count / self.relevant_results_count) * 100

    def __str__(self):
        return f"Research for {self.project.title} on {self.date.strftime('%Y-%m-%d')}"

class ItemContext(models.Model):
    research = models.ForeignKey(Research, on_delete=models.CASCADE, related_name='contexts')
    title = models.CharField(max_length=500)
    description = models.TextField(null=True, blank=True)
    url = models.URLField(max_length=1024, unique=True)
    summary = models.TextField(null=True, blank=True)
    is_relevant = models.BooleanField(default=False)
    
    def __str__(self):
        return self.title

class Opportunity(models.Model):
    research = models.ForeignKey(Research, on_delete=models.CASCADE, related_name='opportunities')
    source_context = models.ForeignKey(ItemContext, on_delete=models.SET_NULL, null=True, related_name='opportunities')
    origin = models.CharField(max_length=255)
    description = models.TextField()
    financing = models.TextField(null=True, blank=True)
    requirements = models.TextField(null=True, blank=True)
    deadline = models.DateTimeField(null=True, blank=True)
    url_to = models.URLField(max_length=1024)
    type = models.CharField(max_length=100)
    
    def __str__(self):
        return f"{self.origin} - {self.type}"

class Report(models.Model):
    research = models.OneToOneField(Research, on_delete=models.CASCADE, related_name='report')
    date = models.DateTimeField(auto_now_add=True)
    path = models.CharField(max_length=1024, help_text="Ruta al archivo del reporte generado")

    def __str__(self):
        return f"Report for {self.research}"

class Note(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='notes')
    date = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=255)
    content = models.TextField()
    type = models.CharField(max_length=50)

    def __str__(self):
        return self.title