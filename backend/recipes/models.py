from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator

from ingredient.models import Ingredient


User = get_user_model()


class Recipe(models.Model):
    name = models.CharField(
        verbose_name="Название рецепта",
        max_length=128,
        db_index=True,
    )
    author = models.ForeignKey(
        User,
        related_name="recipes",
        verbose_name="Автор рецепта",
        on_delete=models.CASCADE,
        db_index=True,
    )
    text = models.TextField(verbose_name="Описание")
    image = models.ImageField(
        verbose_name="Фотография блюда",
        upload_to="recipes_photo/",
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        verbose_name="Ингредиенты",
        through="RecipeIngredient",
        related_name="recipes",
        blank=False,
    )
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name="Время приготовления (минуты)",
        validators=[
            MinValueValidator(
                1,
                message="Время не может быть меньше 1 минуты",
            ),
        ],
    )
    created_at = models.DateTimeField(
        verbose_name="Дата создания",
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        verbose_name = "Рецепт"
        verbose_name_plural = "Рецепты"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class Favorite(models.Model):
    user = models.ForeignKey(
        User, verbose_name="Пользователь", on_delete=models.CASCADE
    )
    recipe = models.ForeignKey(Recipe, verbose_name="Рецепты", on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Избранное"
        verbose_name_plural = "Избранные"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "recipe"], name="unique_user_recipe_in_favorites"
            )
        ]

    def __str__(self):
        return f"{self.user} {self.recipe}"


class Follow(models.Model):
    user = models.ForeignKey(
        User,
        verbose_name="подписчик",
        related_name="follower",
        on_delete=models.CASCADE,
    )
    author = models.ForeignKey(
        User,
        verbose_name="Автор рецепта",
        related_name="following",
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "author"], name="unique_user_author_subscription"
            ),
            models.CheckConstraint(
                check=~models.Q(user=models.F("author")), name="prevent_self_follow"
            ),
        ]

    def __str__(self):
        return f"{self.user} {self.author}"
