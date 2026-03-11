from django.db import models

class SessioneImportazione(models.Model):
    """Memorizza i metadati di ogni operazione ETL eseguita."""
    data_operazione = models.DateTimeField(auto_now_add=True, verbose_name="Data Importazione")
    nome_file_principale = models.CharField(max_length=255, verbose_name="File Sorgente Principale")
    totale_dipendenti = models.IntegerField(default=0, verbose_name="N. Dipendenti Totali")
    costo_totale_periodo = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Costo Totale Periodo")

    class Meta:
        verbose_name = "Sessione di Importazione"
        verbose_name_plural = "Storico Importazioni ETL"

class RecordStoricoDipendente(models.Model):
    """
    Rappresenta il 'fermo immagine' dei dati consolidati per ogni dipendente.
    L'aggancio avviene tramite la combinazione Azienda + Matricola.
    """
    sessione = models.ForeignKey(SessioneImportazione, on_delete=models.CASCADE, related_name='records')
    
    # AGGANCIO AZIENDALE
    codice_azienda = models.CharField(max_length=50, verbose_name="Codice Azienda")
    ragione_sociale = models.CharField(max_length=255, verbose_name="Ragione Sociale")
    
    # IDENTIFICAZIONE E ANAGRAFICA DETTAGLIATA
    matricola = models.CharField(max_length=50, verbose_name="Matricola")
    nominativo = models.CharField(max_length=255, verbose_name="Nominativo")
    qualifica = models.CharField(max_length=100, blank=True, null=True, verbose_name="Qualifica")
    tipo_contratto = models.CharField(max_length=100, blank=True, null=True, verbose_name="Tempo det/indet")
    livello = models.CharField(max_length=50, blank=True, null=True, verbose_name="Livello")
    perc_part_time = models.DecimalField(max_digits=5, decimal_places=2, default=100, verbose_name="Perc. Part time")
    tipo_retribuzione = models.CharField(max_length=50, blank=True, null=True, verbose_name="Tipo Retribuzione")
    
    # DATE CONTRATTUALI
    data_assunzione = models.CharField(max_length=50, blank=True, null=True, verbose_name="Data assunzione")
    data_cessazione = models.CharField(max_length=50, blank=True, null=True, verbose_name="Data cessazione")
    data_cessazione_prevista = models.CharField(max_length=50, blank=True, null=True, verbose_name="Data cessazione prevista")
    
    # SINTESI ECONOMICA E RETRIBUZIONE DI FATTO
    lordo = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Lordo Mensile")
    retribuzione_di_fatto = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Retribuzione di Fatto")
    costo_aziendale = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Costo Aziendale")
    netto_stimato = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Netto Busta")
    
    # CONTRIBUTI E TFR (STACOS)
    inps_ditta = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="INPS Ditta")
    inail_ditta = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="INAIL Ditta")
    tfr_quota_mese = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="TFR Mese")

    # PRESENZE E ORE
    ore_ordinarie = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Ore Ordinarie")
    ore_straordinarie = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Ore Straordinarie")

    # I 18 ELEMENTI RETRIBUTIVI (I NUOVI CASSETTI)
    elemento_1 = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Elemento 1")
    elemento_2 = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Elemento 2")
    elemento_3 = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Elemento 3")
    elemento_4 = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Elemento 4")
    elemento_5 = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Elemento 5")
    elemento_6 = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Elemento 6")
    elemento_7 = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Elemento 7")
    elemento_8 = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Elemento 8")
    elemento_9 = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Elemento 9")
    elemento_10 = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Elemento 10")
    elemento_11 = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Elemento 11")
    elemento_12 = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Elemento 12")
    elemento_13 = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Elemento 13")
    elemento_14 = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Elemento 14")
    elemento_15 = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Elemento 15")
    elemento_16 = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Elemento 16")
    elemento_17 = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Elemento 17")
    elemento_18 = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Elemento 18")

    # RATEI E RESIDUI (CON NUOVI CAMPI MATURATO)
    ferie_residue = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Ferie Residue")
    ferie_maturate = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Ferie Maturate") # NUOVO CAMPO
    permessi_residui = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Permessi Residui")
    permessi_maturati = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Permessi Maturati") # NUOVO CAMPO
    rol_residuo = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Rol Residuo")
    rol_maturato = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Rol Maturato") # NUOVO CAMPO
    ex_fest_residuo = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="ExFes Residuo")
    ex_fest_maturato = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="ExFes Maturato") # NUOVO CAMPO
    
    # PAYLOAD INTEGRALE (Per dati grezzi extra)
    dati_completi_json = models.JSONField(default=dict, verbose_name="Dati Integrali")

    class Meta:
        verbose_name = "Record Storico Dipendente"
        verbose_name_plural = "Records Storici"
        unique_together = ('sessione', 'codice_azienda', 'matricola')

class ConfigurazioneMapper(models.Model):
    """Salva i profili di mappatura per automatizzare i caricamenti futuri."""
    nome_profilo = models.CharField(max_length=100, unique=True, default="Ranocchi Standard")
    mappatura_json = models.JSONField(verbose_name="Mappatura Colonne")

    class Meta:
        verbose_name = "Profilo Mappatura"
        verbose_name_plural = "Profili Mappatura"