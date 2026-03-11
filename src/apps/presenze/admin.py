from django.contrib import admin
from .models import FoglioMensile

@admin.register(FoglioMensile)
class FoglioMensileAdmin(admin.ModelAdmin):
    list_display = ('dipendente', 'mese', 'anno')
    list_filter = ('mese', 'dipendente')