from django.contrib import admin

from recipes.models import RecipeIngredient, RecipeShortLink

from .models import (
    Ingredient,
)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("name", "measurement_unit")
    search_fields = ("name",)
    list_filter = ("name",)


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ("recipe", "ingredient", "amount")
    search_fields = ("recipe__name", "ingredient__name")
    list_filter = ("recipe", "ingredient")


@admin.register(RecipeShortLink)
class RecipeShortLinkAdmin(admin.ModelAdmin):
    list_display = ("recipe", "url_hash", "created_at")
    search_fields = ("recipe__name", "url_hash")
    list_filter = ("created_at",)
