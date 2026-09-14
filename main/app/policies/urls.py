"""policies routes; public names and paths remain stable."""
from django.urls import path
from . import views

urlpatterns = [
    path('policies', views.policies, name='policies'),
]
