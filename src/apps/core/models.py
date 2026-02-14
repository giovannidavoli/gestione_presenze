from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    # Qui puoi aggiungere campi personalizzati in futuro
    # Per ora lo lasciamo così per sbloccare l'errore
    pass