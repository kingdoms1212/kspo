"""dashboard routes; public names and paths remain stable."""
from django.urls import path
from . import views
from . import plan_views, ai_views

urlpatterns = [
    path('dashboard/ai/region', ai_views.region_review, name='region_review'),
    path('dashboard/ai/plan', ai_views.plan_review, name='plan_review'),
    path('dashboard', views.dashboard, name='dashboard'),
    path('dashboard/plan/facilities', plan_views.facility_list, name='plan_facilities'),
    path('dashboard/plan/facility', plan_views.facility_detail, name='plan_facility_detail'),
    path('dashboard/plan/preview', plan_views.preview, name='plan_preview'),
    path('dashboard/plan/restore', plan_views.restore, name='plan_restore'),
]
