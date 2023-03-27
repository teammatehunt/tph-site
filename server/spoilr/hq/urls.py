from django.urls import path, re_path

from .views import handler_views, task_views

from . import dashboard

app_name = "spoilr.hq"
urlpatterns = [
    path(
        "handler/sign-in/", handler_views.handler_sign_in_view, name="handler_sign_in"
    ),
    path(
        "handler/sign-out/",
        handler_views.handler_sign_out_view,
        name="handler_sign_out",
    ),
    path("handler/stats/", handler_views.handler_stats, name="handler_stats"),
    path("task/claim/", task_views.task_claim_view, name="task_claim"),
    path("task/unclaim/", task_views.task_unclaim_view, name="task_unclaim"),
    path("task/snooze/", task_views.task_snooze_view, name="task_snooze"),
    path("task/ignore/", task_views.task_ignore_view, name="task_ignore"),
    path("", dashboard.dashboard, name="dashboard"),
]
