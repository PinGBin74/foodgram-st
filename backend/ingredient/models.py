from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator

from backend.recipes.models import Recipe


User = get_user_model()


class Ingredient(models.Model):
    name = models.CharField(
        verbose_name="Название ингредиента",
        max_length=128,
        unique=True,
        db_index=True,
    )
    measurement_unit = models.CharField(
        verbose_name="Единица измерения",
        max_length=128,
    )

    class Meta:
        verbose_name = "Ингредиент"
        verbose_name_plural = "Ингредиенты"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}, {self.measurement_unit}"


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        verbose_name="Рецепт",
        on_delete=models.CASCADE,
        related_name="ingredients_items",
    )
    ingredient = models.ForeignKey(
        Ingredient,
        verbose_name="Ингредиент",
        on_delete=models.CASCADE,
    )
    amount = models.PositiveSmallIntegerField(
        verbose_name="Количество",
        validators=[MinValueValidator(1, message="Количество не может быть менее 1")],
    )

    class Meta:
        verbose_name = "Ингридиент рецепта"
        verbose_name_plural = "Ингридиенты рецептов"

    def __str__(self):
        name = self.ingredient.name
        amount = self.amount
        unit = self.ingredient.measurement_unit
        return f"{name} - {amount} {unit}"


class RecipeShortLink(models.Model):
    recipe = models.ForeignKey(Recipe, verbose_name="Рецепт", on_delete=models.CASCADE)
    url_hash = models.CharField(
        verbose_name="Хэш", max_length=10, unique=True, db_index=True
    )
    created_at = models.DateTimeField(
        verbose_name="Дата создания ссылки", auto_now_add=True
    )

    class Meta:
        verbose_name = "Короткая ссылка на рецепт"
        verbose_name_plural = "Короткие ссылки на рецепты"

    def __str__(self):
        return f"{self.url_hash} -> {self.recipe.name}"
