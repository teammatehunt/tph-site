from django.conf import settings
from django.urls import path, re_path

from .views import action_views, dashboard_views

app_name = "spoilr.email"
urlpatterns = [
    path("emails/", dashboard_views.dashboard_view, name="dashboard"),
    path("emails/archive/", dashboard_views.archive_view, name="archive"),
    path("emails/send", action_views.send_view, name="send"),
    path("emails/reply", action_views.reply_view, name="reply"),
]
