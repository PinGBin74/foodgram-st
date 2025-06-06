# Generated by Django 4.2.21 on 2025-06-05 14:12

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Favorite",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
            ],
            options={
                "verbose_name": "Избранное",
                "verbose_name_plural": "Избранное",
            },
        ),
        migrations.CreateModel(
            name="Recipe",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Название рецепта",
                        max_length=256,
                        verbose_name="Название",
                    ),
                ),
                (
                    "image",
                    models.ImageField(
                        help_text="Картинка рецепта",
                        upload_to="recipes/images/",
                        verbose_name="Картинка",
                    ),
                ),
                (
                    "text",
                    models.TextField(
                        help_text="Описание рецепта", verbose_name="Описание"
                    ),
                ),
                (
                    "cooking_time",
                    models.PositiveIntegerField(
                        help_text="Время приготовления в минутах",
                        validators=[django.core.validators.MinValueValidator(1)],
                        verbose_name="Время приготовления",
                    ),
                ),
                (
                    "pub_date",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Дата публикации рецепта",
                        verbose_name="Дата публикации",
                    ),
                ),
            ],
            options={
                "verbose_name": "Рецепт",
                "verbose_name_plural": "Рецепты",
                "ordering": ["-pub_date"],
            },
        ),
        migrations.CreateModel(
            name="RecipeIngredient",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "amount",
                    models.PositiveIntegerField(
                        help_text="Количество ингредиента",
                        validators=[django.core.validators.MinValueValidator(1)],
                        verbose_name="Количество",
                    ),
                ),
            ],
            options={
                "verbose_name": "Ингредиент в рецепте",
                "verbose_name_plural": "Ингредиенты в рецептах",
            },
        ),
        migrations.CreateModel(
            name="ShoppingCart",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "recipe",
                    models.ForeignKey(
                        help_text="Рецепт в списке покупок",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="in_shopping_cart",
                        to="recipe.recipe",
                        verbose_name="Рецепт",
                    ),
                ),
            ],
            options={
                "verbose_name": "Список покупок",
                "verbose_name_plural": "Списки покупок",
            },
        ),
    ]
