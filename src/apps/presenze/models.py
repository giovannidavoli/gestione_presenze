from django.db import models
from apps.anagrafica.models import Dipendente

class FoglioMensile(models.Model):
    """
    Rappresenta la tabella 'presenze_fogliomensile' richiesta dal database.
    Memorizza le ore lavorate giorno per giorno per ogni dipendente.
    """
    dipendente = models.ForeignKey(
        Dipendente, 
        on_delete=models.CASCADE, 
        related_name='fogli_presenze',
        verbose_name="Dipendente"
    )
    mese = models.IntegerField(verbose_name="Mese")
    anno = models.IntegerField(verbose_name="Anno")

    # Campi per i 31 giorni del mese (ore lavorate)
    giorno_1 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    giorno_2 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    giorno_3 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    giorno_4 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    giorno_5 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    giorno_6 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    giorno_7 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    giorno_8 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    giorno_9 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    giorno_10 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    giorno_11 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    giorno_12 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    giorno_13 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    giorno_14 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    giorno_15 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    giorno_16 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    giorno_17 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    giorno_18 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    giorno_19 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    giorno_20 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    # Prosegue fino a 31 per coprire tutti i mesi
    giorno_21 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    giorno_22 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    giorno_23 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    giorno_24 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    giorno_25 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    giorno_26 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    giorno_27 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    giorno_28 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    giorno_29 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    giorno_30 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    giorno_31 = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Foglio Presenze Mensile"
        verbose_name_plural = "Fogli Presenze Mensili"
        unique_together = ('dipendente', 'mese', 'anno')

    def __str__(self):
        return f"{self.dipendente.cognome_nome} - {self.mese}/{self.anno}"