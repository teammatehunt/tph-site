from django.urls import path, re_path

from . import views

app_name = "spoilr.hints"
urlpatterns = [
    path("", views.dashboard_view, name="dashboard"),
    re_path("^(?P<puzzle>[^/]+)/canned/$", views.canned_hints_view, name="canned"),
    re_path(
        "^(?P<puzzle>[^/]+)/history/(?P<team>[^/]+)$",
        views.history_view,
        name="history",
    ),
    path("respond/", views.respond_view, name="respond"),
]
