"""programs routes; public names and paths remain stable."""
from django.urls import path
from . import views

urlpatterns = [
    path('programs', views.programs, name='programs'),
    path('export/programs.xlsx', views.export_programs, name='export_programs'),
]
