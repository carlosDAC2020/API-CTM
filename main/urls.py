# task_app/urls.py
from django.urls import path
from . import views

#app_name = "main"

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('start-task/', views.start_task_view, name='start_task'),
    path('task-status/<str:task_id>/', views.task_status_view, name='task_status'),
]