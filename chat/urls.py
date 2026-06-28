from django.urls import path
from . import views

urlpatterns = [
    path("notifications/", views.get_chats_preview, name="notifications"),
    
]