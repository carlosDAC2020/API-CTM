from django.urls import path
from . import views

urlpatterns = [
    path('test-sender/', views.test_sender_view, name='test_sender'),
    path('send-notification/', views.send_notification_view, name='send_notification'),
]