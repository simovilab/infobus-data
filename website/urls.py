from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("health/", views.health_check, name="health_check"),
    path("test-reload/", views.hot_reload_test, name="hot_reload_test"),
]
