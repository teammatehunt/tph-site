from django.urls import path

from . import views

urlpatterns = [
    path("request_reset", views.request_reset),
    path("validate_token", views.validate_token),
    path("reset_password", views.reset_password),
]
