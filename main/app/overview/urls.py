"""overview routes; public names and paths remain stable."""
from django.urls import path

from . import views

urlpatterns = [
    path('overview', views.overview, name='overview'),
]
