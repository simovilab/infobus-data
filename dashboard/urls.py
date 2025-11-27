"""
URL configuration for dashboard app.
"""
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='index'),
    path('api/routes/', views.routes_api, name='routes_api'),
    path('api/stop-times/', views.stop_times_api, name='stop_times_api'),
]
