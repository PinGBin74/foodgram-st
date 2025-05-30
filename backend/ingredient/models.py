from django.db import models
from django.contrib.auth import get_user_model

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
