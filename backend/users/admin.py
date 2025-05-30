from django.contrib import admin
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    search_fields = ("email", "username")
    list_display = ("id", "email", "username",
                    "first_name", "last_name", "password")
    search_help_text = "Поиск по электронной почте и никнейму"
