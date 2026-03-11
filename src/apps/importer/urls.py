from django.urls import path
from . import views

urlpatterns = [
    path('', views.mapper_dashboard, name='importer_dashboard'),
    path('storico/', views.storico_dashboard, name='importer_storico'),
]