"""facilities routes; public names and paths remain stable."""
from django.urls import path
from . import views

urlpatterns = [
    path('facilities', views.facilities, name='facilities'),
    path('export/facilities.xlsx', views.export_facilities, name='export_facilities'),
]
