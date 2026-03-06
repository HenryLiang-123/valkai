from django.urls import path
from chat import views

urlpatterns = [
    path("strategies", views.strategies, name="strategies"),
    path("sessions", views.create_session, name="create_session"),
    path("sessions/<uuid:session_id>/messages", views.session_messages, name="session_messages"),
    path("sessions/<uuid:session_id>/send", views.send, name="send"),
]
