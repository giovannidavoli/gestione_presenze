from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

# Questo comando farà apparire la voce "Users" sopra "Groups"
admin.site.register(User, UserAdmin)