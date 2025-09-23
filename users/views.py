
from django.contrib.auth.models import User

from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .serializers import UserSerializer

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = UserSerializer


class ProtectedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Gracias a IsAuthenticated y JWTAuthentication,
        # el usuario autenticado está disponible en request.user
        user = request.user

        # Ahora puedes usar los datos del usuario para construir tu respuesta
        content = {
            'message': f'¡Bienvenido {user.username}! Esta es una vista protegida.',
            'user_id': user.id,
            'user_email': user.email,
            'user_first_name': user.first_name,
            'user_last_name': user.last_name,
        }
        return Response(content)