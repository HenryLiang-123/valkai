from django.urls import path
from chat import views

urlpatterns = [
    path("strategies", views.strategies, name="strategies"),
    path("sessions", views.create_session, name="create_session"),
    path("sessions/list", views.list_sessions, name="list_sessions"),
    path("sessions/<uuid:session_id>/messages", views.session_messages, name="session_messages"),
    path("sessions/<uuid:session_id>/send", views.send, name="send"),
    path("evals/run", views.run_evals, name="run_evals"),
    path("evals/runs", views.list_eval_runs, name="list_eval_runs"),
    path("evals/runs/<uuid:run_id>", views.get_eval_run, name="get_eval_run"),
]
