from django.contrib import admin
from .models import SessioneImportazione, RecordStoricoDipendente, ConfigurazioneMapper

@admin.register(SessioneImportazione)
class SessioneImportazioneAdmin(admin.ModelAdmin):
    list_display = ('id', 'data_operazione', 'nome_file_principale', 'totale_dipendenti', 'costo_totale_periodo')
    readonly_fields = ('data_operazione',)

@admin.register(RecordStoricoDipendente)
class RecordStoricoDipendenteAdmin(admin.ModelAdmin):
    list_display = ('matricola', 'nominativo', 'codice_azienda', 'tipo_retribuzione', 'lordo', 'netto_stimato', 'sessione')
    list_filter = ('codice_azienda', 'sessione')
    search_fields = ('matricola', 'nominativo', 'ragione_sociale')

@admin.register(ConfigurazioneMapper)
class ConfigurazioneMapperAdmin(admin.ModelAdmin):
    list_display = ('nome_profilo',)