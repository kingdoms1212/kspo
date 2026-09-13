"""App-level routes: maps URLs to this app's controller functions (views.py)."""
from django.urls import path

from . import views

urlpatterns = [
    path('dashboard', views.dashboard, name='dashboard'),
    path('programs', views.programs, name='programs'),
    path('facilities', views.facilities, name='facilities'),
    path('export/facilities.csv', views.export_facilities, name='export_facilities'),
    path('export/programs.csv', views.export_programs, name='export_programs'),
]
