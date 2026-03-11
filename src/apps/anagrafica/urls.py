from django.urls import path
from django.contrib.auth import views as auth_views  # <-- NUOVO: Importa il sistema di Login di Django
from . import views

urlpatterns = [
    # --- NUOVE ROTTE PER IL LOGIN E LOGOUT ---
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # 1. Dashboard Generale (Home Page dell'App)
    path('', views.DashboardView.as_view(), name='dashboard_generale'),
    
    # 2. Anteprima sincronizzazione
    path('anteprima/<int:pk>/', views.PreviewSincroView.as_view(), name='prewiew_sincro'),
    
    # 3. Dashboard Azienda (Vista Mensile)
    path('dashboard/<int:pk>/<int:anno>/<int:mese>/', views.dashboard_azienda, name='dashboard_azienda'),
    
    # 4. Esportazione CSV Ranocchi
    path('export-csv/<int:azienda_id>/<int:anno>/<int:mese>/', views.export_csv_view, name='export_csv'),
    
    # 5. Inserimento Massivo
    path('inserimento-massivo/<int:azienda_id>/', views.inserimento_massivo_view, name='inserimento_massivo'),

    # 6. API JSON per il salvataggio
    path('api/salva-presenze/', views.salva_presenze_json, name='salva_presenze_json'),

    # 7. Simulazione Busta Paga
    path('simulazione-cedolino/<int:dipendente_id>/<int:anno>/<int:mese>/', views.simulazione_busta_paga_view, name='simulazione_busta_paga'),

    # 8. Report Costi Aziendali
    path('report-costi/<int:azienda_id>/<int:anno>/<int:mese>/', views.report_costi_azienda_view, name='report_costi_azienda'),

    # 9. API JSON per Azzerare le presenze
    path('api/azzera-presenze/', views.azzera_presenze_json, name='azzera_presenze_json'),
]