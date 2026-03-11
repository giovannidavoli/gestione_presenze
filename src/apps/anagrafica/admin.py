from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.contrib import messages
from datetime import date
from .models import (
    Studio, Azienda, Dipendente, CaricamentoDati, 
    ConfigurazioneMappatura, CCNL, CausaleAssenza, 
    PresenzaGiornaliera, EventoAssenza
)
from .services import importa_dati_excel_gestionale

# ==============================================================================
# 1. GESTIONE CAUSALI E REGISTRO GIORNALIERO
# ==============================================================================

@admin.register(CausaleAssenza)
class CausaleAssenzaAdmin(admin.ModelAdmin):
    """Gestione dei codici causale importati dal file Ranocchi."""
    list_display = ('codice', 'descrizione', 'tipo_causale', 'incide_su_rateo')
    list_filter = ('tipo_causale', 'incide_su_rateo')
    search_fields = ('codice', 'descrizione')

class EventoAssenzaInline(admin.TabularInline):
    """Permette di inserire più assenze diverse nello stesso giorno."""
    model = EventoAssenza
    extra = 1

@admin.register(PresenzaGiornaliera)
class PresenzaGiornalieraAdmin(admin.ModelAdmin):
    """Registro giornaliero: Ore lavorate e di cui notturne (Riga 1 e 2 Ranocchi)."""
    list_display = ('dipendente', 'data', 'ore_lavorate', 'di_cui_notturne', 'is_festivo')
    list_filter = ('data', 'dipendente__azienda', 'is_festivo')
    search_fields = ('dipendente__cognome_nome', 'dipendente__codice')
    inlines = [EventoAssenzaInline]

# ==============================================================================
# 2. PANNELLO DIPENDENTE (ANAGRAFICA, COSTI E RATEI)
# ==============================================================================

@admin.register(Dipendente)
class DipendenteAdmin(admin.ModelAdmin):
    """Pannello completo del dipendente con analisi costi e ratei a 4 stati."""
    list_display = (
        'cognome_nome', 'codice', 'azienda', 'perc_part_time', 
        'lordo_mensile_calcolato'
    )
    list_filter = ('azienda', 'tipo_paga')
    search_fields = ('cognome_nome', 'codice')
    
    # AZIONI MASSIVE
    actions = ['applica_pianificato_mese_corrente']

    @admin.action(description="📅 Copia Pianificato (Mese Corrente)")
    def applica_pianificato_mese_corrente(self, request, queryset):
        """Richiama il service per riempire il mese in base all'orario settimanale."""
        oggi = date.today()
        successi = 0
        from .services import applica_pianificato_mensile
        for dip in queryset:
            try:
                applica_pianificato_mensile(dip, oggi.year, oggi.month)
                successi += 1
            except Exception as e:
                self.message_user(request, f"Errore per {dip}: {str(e)}", level=messages.ERROR)
        
        self.message_user(request, f"Pianificato applicato con successo per {successi} dipendenti.", level=messages.SUCCESS)

    readonly_fields = (
        'totale_paga_tabellare_individuale', 
        'lordo_mensile_base_calcolato',
    )
    
    fieldsets = (
        ('Dati Base e Sede', {
            'fields': (
                'azienda', 'ccnl', 'codice', 'cognome_nome', 
                'sede_lavoro', 'qualifica', 'livello'
            )
        }),
        ('Contratto e Turnover', {
            'fields': (
                ('indirizzo', 'comune'), 
                ('tipo_contratto', 'tipo_paga', 'perc_part_time'), 
                ('data_assunzione', 'data_cessazione', 'data_termine')
            )
        }),
        ('Dettaglio Paga GIS (18 Elementi)', {
            'fields': (
                ('elemento_1', 'elemento_2', 'elemento_3'),
                ('elemento_4', 'elemento_5', 'elemento_6'),
                ('elemento_7', 'elemento_8', 'elemento_9'),
                ('elemento_10', 'elemento_11', 'elemento_12'),
                ('elemento_13', 'elemento_14', 'elemento_15'),
                ('elemento_16', 'elemento_17', 'elemento_18'),
                'totale_paga_tabellare_individuale'
            )
        }),
        ('Analisi Costi BI', {
            'fields': (
                'lordo_mensile_base_calcolato',
                'lordo_mensile_calcolato', 
                'costo_inps_ditta', 
                'costo_inail_ditta', 
                'rateo_tfr', 
                'banca_ore_residuo',
                'notturno_standard'
            )
        }),
        ('Ratei Ferie (4 Stati)', {
            'fields': (('ferie_residuo_ap', 'ferie_maturate', 'ferie_godute', 'ferie_residuo_attuale'),)
        }),
        ('Ratei Permessi / PAR (4 Stati)', {
            'fields': (('permessi_residuo_ap', 'permessi_maturati', 'permessi_goduti', 'permessi_residuo_attuale'),)
        }),
        ('Ratei ROL (4 Stati)', {
            'fields': (('rol_residuo_ap', 'rol_maturati', 'rol_goduti', 'rol_residuo_attuale'),)
        }),
        ('Ratei Ex Festività (4 Stati)', {
            'fields': (('ex_fest_residuo_ap', 'ex_fest_maturati', 'ex_fest_goduti', 'ex_fest_residuo_attuale'),)
        }),
        ('Orario Settimanale', {
            'fields': (
                'ore_lun', 'ore_mar', 'ore_mer', 'ore_gio', 'ore_ven', 'ore_sab', 'ore_dom'
            )
        }),
    )

# ==============================================================================
# 3. AZIENDE E CCNL (CON TASTO DASHBOARD)
# ==============================================================================

@admin.register(Azienda)
class AziendaAdmin(admin.ModelAdmin):
    list_display = ('codice', 'ragione_sociale', 'ccnl', 'tasto_dashboard')
    search_fields = ('ragione_sociale', 'codice')

    def tasto_dashboard(self, obj):
        """Genera il link rapido per la dashboard economica mensile."""
        oggi = date.today()
        url = reverse('dashboard_azienda', args=[obj.pk, oggi.year, oggi.month])
        return format_html(
            '<a class="button" href="{}" style="background-color: #28a745; color: white; padding: 5px 10px; border-radius: 4px; text-decoration: none;">'
            '📊 Dashboard Costi'
            '</a>', url
        )
    tasto_dashboard.short_description = "Analisi Economica"

@admin.register(CCNL)
class CCNLAdmin(admin.ModelAdmin):
    """Gestione parametri CCNL con coefficiente netto stima."""
    list_display = ('nome', 'divisore_orario_standard', 'magg_notturna', 'coeff_netto_stima')

# ==============================================================================
# 4. MAPPATURA INTEGRALE (VARIAZIONI PRESENZE E AGGANCIO AZIENDA)
# ==============================================================================

@admin.register(ConfigurazioneMappatura)
class MappaturaAdmin(admin.ModelAdmin):
    """Configurazione integrale delle colonne Excel per GIS Ranocchi."""
    list_display = ('nome_software', 'data_creazione')
    
    fieldsets = (
        ('Informazioni Generali', {'fields': ('nome_software',)}),
        ('Anagrafica (File: anagrafica.xls)', {
            'fields': (
                'ana_riga_inizio', 
                ('ana_col_azienda_cod', 'ana_col_azienda_ragione'),
                'ana_col_sede_lavoro',
                ('ana_col_matricola', 'ana_col_nominativo'),
                ('ana_col_indirizzo', 'ana_col_comune'),
                ('ana_col_qualifica', 'ana_col_tipo_contratto', 'ana_col_livello'),
                ('ana_col_perc_part_time', 'ana_col_assunzione'),
                ('ana_col_cessazione', 'ana_col_termine'),
            )
        }),
        ('Presenze (File ZIP: PRE...csv)', {
            'description': 'Mappatura per l\'estrazione dalla matrice orizzontale Ranocchi.',
            'fields': (
                'pre_riga_inizio', 
                'pre_col_matricola', 
                'pre_col_tipo',
                'pre_col_azienda_cod'
            )
        }),
        ('Retribuzioni (File: retribuzionipiuaziende.xls)', {
            'fields': (
                'ret_riga_inizio', 
                ('ret_col_azienda_cod', 'ret_col_matricola'),
                ('ret_col_tipo_paga', 'ret_col_lordo_fatto'),
                'ret_col_elementi_start',
            )
        }),
        ('Costi (File: stacos.xls)', {
            'description': 'Mappatura per l\'aggancio costi con riferimento Azienda.',
            'fields': (
                'sta_col_azienda_cod',
                'sta_col_matricola', 
                ('sta_col_inps', 'sta_col_inail', 'sta_col_tfr'),
            )
        }),
        ('Ratei (File: ratei.xls - 16 Colonne)', {
            'description': 'Mappatura completa con riferimento Azienda e 4 stati per rateo.',
            'fields': (
                'rat_col_azienda_cod',
                'rat_col_matricola',
                ('rat_col_ferie_ap', 'rat_col_ferie_mat', 'rat_col_ferie_god', 'rat_col_ferie_res'),
                ('rat_col_perm_ap', 'rat_col_perm_mat', 'rat_col_perm_god', 'rat_col_perm_res'),
                ('rat_col_rol_ap', 'rat_col_rol_mat', 'rat_col_rol_god', 'rat_col_rol_res'),
                ('rat_col_exfest_ap', 'rat_col_exfest_mat', 'rat_col_exfest_god', 'rat_col_exfest_res'),
            )
        }),
    )

# ==============================================================================
# 5. CARICAMENTO DATI E SINCRONIZZAZIONE
# ==============================================================================

@admin.register(CaricamentoDati)
class CaricamentoDatiAdmin(admin.ModelAdmin):
    list_display = ('id', 'data_operazione', 'mappatura', 'tasto_anteprima')
    actions = ['avvia_sincronizzazione_totale']

    def tasto_anteprima(self, obj):
        try:
            url = reverse('prewiew_sincro', args=[obj.pk]) 
            return format_html(
                '<a class="button" href="{}" style="background-color: #264b5d; color: white; padding: 5px 15px; border-radius: 4px; text-decoration: none;">'
                '👁️ Vedi Anteprima'
                '</a>', url
            )
        except Exception: return mark_safe('<span style="color: gray;">-</span>')

    tasto_anteprima.short_description = "Anteprima"

    @admin.action(description="AVVIA SINCRONIZZAZIONE TOTALE")
    def avvia_sincronizzazione_totale(self, request, queryset):
        for obj in queryset:
            try:
                log_msgs = importa_dati_excel_gestionale(obj)
                if log_msgs:
                    html_report = "".join([f"<li style='margin-bottom:5px;'>{m}</li>" for m in log_msgs])
                    self.message_user(request, mark_safe(f"<strong>Esito Operazione:</strong><ul>{html_report}</ul>"), level=messages.INFO)
                else:
                    self.message_user(request, "Sincronizzazione terminata.", level=messages.SUCCESS)
            except Exception as e:
                self.message_user(request, f"Errore critico: {str(e)}", level=messages.ERROR)

# ==============================================================================
# 6. REGISTRAZIONE FINALE (CORREZIONE DOPPIO REGISTRO)
# ==============================================================================

# Rimosso PresenzaGiornaliera da qui perché già registrato con @admin.register a riga 42
admin.site.register([Studio, EventoAssenza])