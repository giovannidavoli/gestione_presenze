from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # --- ROTTA PER RECUPERO PASSWORD DI DJANGO ---
    path('accounts/', include('django.contrib.auth.urls')),
    
    path('', include('apps.anagrafica.urls')),
    path('importer/', include('apps.importer.urls')), # Il nuovo modulo standalone
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)