"""dashboard routes; public names and paths remain stable."""
from django.urls import path
from . import views
from . import plan_views

urlpatterns = [
    path('dashboard', views.dashboard, name='dashboard'),
    path('dashboard/plan/facilities', plan_views.facility_list, name='plan_facilities'),
    path('dashboard/plan/facility', plan_views.facility_detail, name='plan_facility_detail'),
    path('dashboard/plan/preview', plan_views.preview, name='plan_preview'),
]
