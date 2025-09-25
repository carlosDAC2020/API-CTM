from rest_framework import serializers
from .models import Project

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        # 'user' se manejará automáticamente, 'id' y 'created_at' son de solo lectura
        fields = ['id', 'title', 'description', 'keywords', 'created_at']
        read_only_fields = ['id', 'created_at']