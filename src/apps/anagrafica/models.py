from django.db import models
from decimal import Decimal
from django.conf import settings

# ==============================================================================
# 1. STRUTTURA PROFESSIONALE (STUDIO E CCNL)
# ==============================================================================

class Studio(models.Model):
    nome = models.CharField(max_length=255, verbose_name="Nome Studio Professionale")
    sede = models.CharField(max_length=255, verbose_name="Sede Studio")
    partita_iva = models.CharField(max_length=11, null=True, blank=True, verbose_name="Partita IVA")
    # AGGIUNTO: Campo per il logo dello studio utile nella simulazione busta paga
    logo = models.ImageField(upload_to='loghi_studio/', null=True, blank=True, verbose_name="Logo Studio")
    
    def __str__(self): return self.nome
    class Meta:
        verbose_name_plural = "1. Studio di Consulenza (Unico)"

class CCNL(models.Model):
    """Parametri contrattuali per calcoli di maggiorazione e maturazione ratei."""
    nome = models.CharField(max_length=100, verbose_name="Nome Contratto")
    divisore_orario_standard = models.DecimalField(max_digits=6, decimal_places=2, default=173.00, verbose_name="Divisore Contrattuale")
    
    # --- NUOVO CAMPO AGGIUNTO PER GESTIRE 13esima o 14esima ---
    mensilita = models.IntegerField(default=13, verbose_name="Numero Mensilità (13 o 14)")

    # --- MAGGIORAZIONI (%) ---
    magg_supplementare = models.DecimalField(max_digits=5, decimal_places=2, default=10.00, verbose_name="% Lavoro Suppl.")
    magg_straordinario = models.DecimalField(max_digits=5, decimal_places=2, default=15.00, verbose_name="% Lavoro Straord.")
    magg_domenicale = models.DecimalField(max_digits=5, decimal_places=2, default=30.00, verbose_name="% Lavoro Domenicale")
    magg_festivo = models.DecimalField(max_digits=5, decimal_places=2, default=50.00, verbose_name="% Lavoro Festivo")
    magg_notturna = models.DecimalField(max_digits=5, decimal_places=2, default=20.00, verbose_name="% Lavoro Notturno")

    # --- PARAMETRI MATURAZIONE MENSILE (Valori per Full-Time) ---
    mat_ferie_mese = models.DecimalField(max_digits=6, decimal_places=3, default=2.166, verbose_name="Ferie maturate/mese")
    mat_rol_mese = models.DecimalField(max_digits=6, decimal_places=3, default=4.666, verbose_name="ROL maturati/mese")
    mat_exfest_mese = models.DecimalField(max_digits=6, decimal_places=3, default=2.666, verbose_name="Ex Fest maturate/mese")

    # --- STIME DASHBOARD ---
    coeff_netto_stima = models.DecimalField(max_digits=4, decimal_places=2, default=0.75, help_text="Coefficiente per stima netto (es. 0.75)")

    def __str__(self): return self.nome
    class Meta:
        verbose_name_plural = "2. Schede CCNL (Parametri)"

# ==============================================================================
# 2. CONFIGURAZIONE IMPORTAZIONE (MAPPATURA COLONNE)
# ==============================================================================

class ConfigurazioneMappatura(models.Model):
    """Mappatura Ranocchi GIS - Definisce la posizione dei dati nei file Excel."""
    nome_software = models.CharField(max_length=100, default="Ranocchi GIS")
    data_creazione = models.DateTimeField(auto_now_add=True)
    
    # --- ANAGRAFICA (anagrafica.xls) ---
    ana_riga_inizio = models.IntegerField(default=2)
    ana_col_azienda_cod = models.IntegerField(default=0)
    ana_col_azienda_ragione = models.IntegerField(default=2)
    ana_col_sede_lavoro = models.IntegerField(default=3)
    ana_col_matricola = models.IntegerField(default=4)
    ana_col_nominativo = models.IntegerField(default=5)
    ana_col_indirizzo = models.IntegerField(default=6)
    ana_col_comune = models.IntegerField(default=7)
    ana_col_qualifica = models.IntegerField(default=8)
    ana_col_tipo_contratto = models.IntegerField(default=9)
    ana_col_livello = models.IntegerField(default=10)
    ana_col_perc_part_time = models.IntegerField(default=11)
    ana_col_assunzione = models.IntegerField(default=12)
    ana_col_cessazione = models.IntegerField(default=13)
    ana_col_termine = models.IntegerField(default=14)

    # --- AGGIUNTA: PRESENZE (ZIP PRE...csv) ---
    pre_riga_inizio = models.IntegerField(default=4, verbose_name="Riga Inizio Presenze")
    pre_col_matricola = models.IntegerField(default=0, verbose_name="Colonna Matricola (PRE)")
    pre_col_tipo = models.IntegerField(default=2, verbose_name="Colonna Tipo Riga (PRE)")
    pre_col_azienda_cod = models.IntegerField(default=-1, help_text="-1 se da intestazione")

    # --- RETRIBUZIONI (retribuzionipiuaziende.xls) ---
    ret_riga_inizio = models.IntegerField(default=3)
    ret_col_azienda_cod = models.IntegerField(default=2)
    ret_col_matricola = models.IntegerField(default=6)
    ret_col_tipo_paga = models.IntegerField(default=11)
    ret_col_lordo_fatto = models.IntegerField(default=30)
    ret_col_elementi_start = models.IntegerField(default=12)

    # --- COSTI (stacos.xls) ---
    sta_col_azienda_cod = models.IntegerField(default=2, verbose_name="Col. Azienda (STA)")
    sta_col_matricola = models.IntegerField(default=6)
    sta_col_inps = models.IntegerField(default=13)
    sta_col_inail = models.IntegerField(default=14)
    sta_col_tfr = models.IntegerField(default=31)

    # --- RATEI (ratei.xls - 4 stati per ogni rateo) ---
    rat_col_azienda_cod = models.IntegerField(default=1, verbose_name="Col. Azienda (RAT)")
    rat_col_matricola = models.IntegerField(default=5)
    # Ferie
    rat_col_ferie_ap = models.IntegerField(default=7)
    rat_col_ferie_mat = models.IntegerField(default=8)
    rat_col_ferie_god = models.IntegerField(default=9)
    rat_col_ferie_res = models.IntegerField(default=10)
    # Permessi/PAR
    rat_col_perm_ap = models.IntegerField(default=11)
    rat_col_perm_mat = models.IntegerField(default=12)
    rat_col_perm_god = models.IntegerField(default=13)
    rat_col_perm_res = models.IntegerField(default=14)
    # ROL
    rat_col_rol_ap = models.IntegerField(default=15)
    rat_col_rol_mat = models.IntegerField(default=16)
    rat_col_rol_god = models.IntegerField(default=17)
    rat_col_rol_res = models.IntegerField(default=18)
    # Ex Festività
    rat_col_exfest_ap = models.IntegerField(default=19)
    rat_col_exfest_mat = models.IntegerField(default=20)
    rat_col_exfest_god = models.IntegerField(default=21)
    rat_col_exfest_res = models.IntegerField(default=22)

    def __str__(self): return self.nome_software
    class Meta:
        verbose_name_plural = "Mappature Software"

# ==============================================================================
# 3. GESTIONE CAUSALI RANOCCHI GIS
# ==============================================================================

class CausaleAssenza(models.Model):
    """Tabella delle causali importate dal file 'CAUSALI LAVORO'."""
    codice = models.CharField(max_length=10, unique=True, verbose_name="Codice GIS (es. *FE)")
    descrizione = models.CharField(max_length=255)
    
    TIPO_CHOICES = [
        ('LAVORO', 'Lavoro Ordinario'),
        ('ASSENZA', 'Assenza Retribuita'),
        ('NON_RET', 'Assenza Non Retribuita'),
        ('FEST', 'Festività Goduta'),
    ]
    tipo_causale = models.CharField(max_length=20, choices=TIPO_CHOICES, default='ASSENZA')
    incide_su_rateo = models.CharField(
        max_length=20, 
        choices=[('FERIE','Ferie'),('ROL','ROL'),('PERM','Permessi'),('NESSUNO','Nessuno')], 
        default='NESSUNO'
    )

    def __str__(self): return f"{self.codice} - {self.descrizione}"
    class Meta:
        verbose_name_plural = "6. Causali GIS Ranocchi"

## ==============================================================================
# 4. ANAGRAFICA AZIENDALE E DIPENDENTI
# ==============================================================================

class Azienda(models.Model):
    studio = models.ForeignKey(Studio, on_delete=models.CASCADE, related_name='aziende')
    
    utente = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='azienda_gestita', verbose_name="Utente di Accesso (Cliente)")
    
    codice = models.CharField(max_length=20, unique=True)
    ragione_sociale = models.CharField(max_length=255)
    email_amministrazione = models.EmailField(max_length=255, null=True, blank=True, verbose_name="Email Amministrazione")
    ccnl = models.ForeignKey(CCNL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="CCNL Applicato")
    # AGGIUNTO: Campo logo per visualizzazione intestazione azienda
    logo = models.ImageField(upload_to='loghi_aziende/', null=True, blank=True, verbose_name="Logo Azienda")
    
    giorno_patrono = models.IntegerField(null=True, blank=True, help_text="GG")
    mese_patrono = models.IntegerField(null=True, blank=True, help_text="MM")

    def __str__(self): return f"{self.codice} - {self.ragione_sociale}"
    class Meta:
        verbose_name_plural = "3. Aziende"

class Dipendente(models.Model):
    azienda = models.ForeignKey(Azienda, on_delete=models.CASCADE, related_name='dipendenti')
    ccnl = models.ForeignKey(CCNL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="CCNL Eccezione")
    codice = models.CharField(max_length=20, verbose_name="Matricola GIS") 
    cognome_nome = models.CharField(max_length=255)
    
    sede_lavoro = models.CharField(max_length=255, null=True, blank=True)
    indirizzo = models.CharField(max_length=255, null=True, blank=True)
    comune = models.CharField(max_length=100, null=True, blank=True)
    qualifica = models.CharField(max_length=100, null=True, blank=True)
    livello = models.CharField(max_length=50, null=True, blank=True)
    tipo_contratto = models.CharField(max_length=100, null=True, blank=True)
    tipo_paga = models.CharField(max_length=50, default="Mensile")
    perc_part_time = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    
    notturno_standard = models.DecimalField(max_digits=4, decimal_places=2, default=0.00, verbose_name="Ore Notturne fisse")
    banca_ore_residuo = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Residuo Banca Ore")

    data_assunzione = models.DateField(null=True, blank=True)
    data_cessazione = models.DateField(null=True, blank=True)
    data_termine = models.DateField(null=True, blank=True)

    # Elenco elementi retributivi (1-18)
    elemento_1 = models.DecimalField(max_digits=12, decimal_places=5, default=0)
    elemento_2 = models.DecimalField(max_digits=12, decimal_places=5, default=0)
    elemento_3 = models.DecimalField(max_digits=12, decimal_places=5, default=0)
    elemento_4 = models.DecimalField(max_digits=12, decimal_places=5, default=0)
    elemento_5 = models.DecimalField(max_digits=12, decimal_places=5, default=0)
    elemento_6 = models.DecimalField(max_digits=12, decimal_places=5, default=0)
    elemento_7 = models.DecimalField(max_digits=12, decimal_places=5, default=0)
    elemento_8 = models.DecimalField(max_digits=12, decimal_places=5, default=0)
    elemento_9 = models.DecimalField(max_digits=12, decimal_places=5, default=0)
    elemento_10 = models.DecimalField(max_digits=12, decimal_places=5, default=0)
    elemento_11 = models.DecimalField(max_digits=12, decimal_places=5, default=0)
    elemento_12 = models.DecimalField(max_digits=12, decimal_places=5, default=0)
    elemento_13 = models.DecimalField(max_digits=12, decimal_places=5, default=0)
    elemento_14 = models.DecimalField(max_digits=12, decimal_places=5, default=0)
    elemento_15 = models.DecimalField(max_digits=12, decimal_places=5, default=0)
    elemento_16 = models.DecimalField(max_digits=12, decimal_places=5, default=0)
    elemento_17 = models.DecimalField(max_digits=12, decimal_places=5, default=0)
    elemento_18 = models.DecimalField(max_digits=12, decimal_places=5, default=0)
    
    lordo_mensile_calcolato = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    costo_inps_ditta = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    costo_inail_ditta = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    rateo_tfr = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    ferie_residuo_ap = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    ferie_maturate = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    ferie_godute = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    ferie_residuo_attuale = models.DecimalField(max_digits=12, decimal_places=3, default=0)

    permessi_residuo_ap = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    permessi_maturati = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    permessi_goduti = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    permessi_residuo_attuale = models.DecimalField(max_digits=12, decimal_places=3, default=0)

    rol_residuo_ap = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    rol_maturati = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    rol_goduti = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    rol_residuo_attuale = models.DecimalField(max_digits=12, decimal_places=3, default=0)

    ex_fest_residuo_ap = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    ex_fest_maturati = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    ex_fest_goduti = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    ex_fest_residuo_attuale = models.DecimalField(max_digits=12, decimal_places=3, default=0)

    ore_lun = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    ore_mar = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    ore_mer = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    ore_gio = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    ore_ven = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    ore_sab = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    ore_dom = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

   # ==========================================================================
    # LOGICA DI CALCOLO DINAMICA (CON INTERCETTAZIONE AL SALVATAGGIO)
    # ==========================================================================

    def save(self, *args, **kwargs):
        # 1. Calcolo del tabellare grezzo (somma elementi da 1 a 18 esportati da GIS)
        # Usiamo list comprehension sicura per evitare errori se un campo è None
        tabellare = sum([getattr(self, f'elemento_{i}') or Decimal('0.00') for i in range(1, 19)])
        
        # 2. Intercettiamo e correggiamo il LORDO prima di scriverlo fisicamente nel DB
        tipo = self.tipo_paga.strip().lower() if self.tipo_paga else "mensile"
        
        if tipo in ["oraria", "orario"]:
            # LOGICA ORARIA: Paga oraria (es. 7,59€) moltiplicata per ore medie mensili
            # Formula: (Ore sett. * 52 sett.) / 12 mesi
            ore_sett = sum([self.ore_lun, self.ore_mar, self.ore_mer, self.ore_gio, self.ore_ven, self.ore_sab, self.ore_dom]) or Decimal("0.00")
            ore_medie_mensili = (ore_sett * Decimal("52")) / Decimal("12")
            
            # Assegnazione (anche se è 0, così non rimangono vecchi valori sporchi)
            self.lordo_mensile_calcolato = (tabellare * ore_medie_mensili).quantize(Decimal("0.01"))
        
        else:
            # LOGICA MENSILE: Il tabellare esportato da GIS per i mensilizzati
            # corrisponde GIA' alla loro paga mensile base (anche se part-time).
            # Non dobbiamo riproporzionarlo un'altra volta per la % part_time, 
            # altrimenti rischiamo di abbatterlo due volte!
            self.lordo_mensile_calcolato = tabellare.quantize(Decimal("0.01"))
                
        super(Dipendente, self).save(*args, **kwargs)

    @property
    def contratto_attivo(self):
        return self.ccnl if self.ccnl else self.azienda.ccnl

    @property
    def ore_settimanali(self):
        return sum([self.ore_lun, self.ore_mar, self.ore_mer, self.ore_gio, self.ore_ven, self.ore_sab, self.ore_dom])

    @property
    def totale_paga_tabellare_individuale(self):
        return sum([getattr(self, f'elemento_{i}') or Decimal('0.00') for i in range(1, 19)])

    @property
    def lordo_mensile_base_calcolato(self):
        # Grazie alla funzione save() qui sopra, questo campo nel DB è già perfetto.
        return self.lordo_mensile_calcolato or Decimal("0.00")

    @property
    def calcola_costo_aziendale_mensile_totale(self):
        # Il lordo è già corretto alla fonte. Facciamo solo una semplice somma degli oneri aziendali.
        lordo = self.lordo_mensile_calcolato or Decimal("0.00")
        inps = self.costo_inps_ditta or Decimal("0.00")
        inail = self.costo_inail_ditta or Decimal("0.00")
        tfr = self.rateo_tfr or Decimal("0.00")
        
        return (lordo + inps + inail + tfr).quantize(Decimal("0.01"))

    @property
    def calcola_costo_orario_reale(self):
        # Il costo orario medio per budgeting (usato nella dashboard generale) si basa sulle ore medie mensili
        ore_mese = self.ore_settimanali * Decimal("4.333")
        if ore_mese > 0:
            return (self.calcola_costo_aziendale_mensile_totale / ore_mese).quantize(Decimal("0.01"))
        return Decimal("0.00")

    def __str__(self): 
        return self.cognome_nome
        
    class Meta:
        verbose_name_plural = "5. Anagrafica Dipendenti"
        unique_together = ('azienda', 'codice')
        
# ==============================================================================
# 5. REGISTRO PRESENZE GIORNALIERO (STRUTTURA GIS RANOCCHI)
# ==============================================================================

class PresenzaGiornaliera(models.Model):
    dipendente = models.ForeignKey(Dipendente, on_delete=models.CASCADE, related_name='presenze')
    data = models.DateField()
    
    ore_lavorate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    di_cui_notturne = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    straordinarie = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    is_festivo = models.BooleanField(default=False)
    
    # --- CAMPI AGGIUNTI PER LOGICA SWAP DEI TURNI E FORZATURA ---
    # AGGIUNTO: Permette di marcare esplicitamente un giorno come riposo (vince su contratto)
    is_riposo = models.BooleanField(default=False, verbose_name="Forza Riposo")
    # AGGIUNTO: Campo note per tracciare lo spostamento delle ore o motivi di forzatura
    note = models.CharField(max_length=255, null=True, blank=True, verbose_name="Note Spostamento/Turno")

    class Meta:
        unique_together = ('dipendente', 'data')
        verbose_name_plural = "7. Registro Presenze Giornaliero"

class EventoAssenza(models.Model):
    giornata = models.ForeignKey(PresenzaGiornaliera, on_delete=models.CASCADE, related_name='eventi')
    causale = models.ForeignKey(CausaleAssenza, on_delete=models.PROTECT)
    ore = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        verbose_name_plural = "8. Eventi Assenza (Righe Extra CSV)"

# ==============================================================================
# 6. GESTIONE CARICAMENTI
# ==============================================================================

class CaricamentoDati(models.Model):
    mappatura = models.ForeignKey(ConfigurazioneMappatura, on_delete=models.PROTECT)
    data_operazione = models.DateTimeField(auto_now_add=True)
    file_anagrafica = models.FileField(upload_to='excel/', null=True, blank=True)
    file_retribuzioni = models.FileField(upload_to='excel/', null=True, blank=True)
    file_stacos = models.FileField(upload_to='excel/', null=True, blank=True)
    file_ratei = models.FileField(upload_to='excel/', null=True, blank=True)
    file_presenze = models.FileField(upload_to='presenze_uploads/', verbose_name="ZIP Presenze", null=True, blank=True)
    file_causali_gis = models.FileField(upload_to='causali/', null=True, blank=True, verbose_name="CSV Causali Ranocchi")

    def __str__(self): return f"Caricamento {self.id} - {self.data_operazione}"
    class Meta:
        verbose_name_plural = "Caricamenti Manuali"

# ==============================================================================
# 7. BACHECA NOTE AZIENDALI
# ==============================================================================

class NotaMensileAzienda(models.Model):
    """Cassettino per memorizzare comunicazioni variabili mensili (Premi, Buoni pasto, Trasferte)."""
    azienda = models.ForeignKey(Azienda, on_delete=models.CASCADE, related_name='note_mensili')
    anno = models.IntegerField()
    mese = models.IntegerField()
    testo = models.TextField(blank=True, null=True, verbose_name="Note e Rimborsi")
    data_aggiornamento = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "9. Note Mensili Aziende"
        unique_together = ('azienda', 'anno', 'mese')

    def __str__(self):
        return f"Note {self.azienda.ragione_sociale} - {self.mese}/{self.anno}"