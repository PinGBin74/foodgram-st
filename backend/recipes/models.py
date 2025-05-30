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
        validators=[MinValueValidator(
            1,
            message="Количество не может быть менее 1")],
    )

    class Meta:
        verbose_name = "Ингридиент рецепта"
        verbose_name_plural = "Ингридиенты рецептов"

    def __str__(self):
        name = self.ingredient.name
        amount = self.amount
        unit = self.ingredient.measurement_unit
        return f"{name} - {amount} {unit}"


class Favorite(models.Model):
    user = models.ForeignKey(
        User, verbose_name="Пользователь", on_delete=models.CASCADE
    )
    recipe = models.ForeignKey(Recipe, verbose_name="Рецепты",
                               on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Избранное"
        verbose_name_plural = "Избранные"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "recipe"],
                name="unique_user_recipe_in_favorites"
            )
        ]

    def __str__(self):
        return f"{self.user} {self.recipe}"


class ShoppingCart(models.Model):
    user = models.ForeignKey(
        User, verbose_name="Пользователь", on_delete=models.CASCADE
    )
    recipe = models.ForeignKey(Recipe, verbose_name="Рецепт",
                               on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Корзина покупок"
        verbose_name_plural = "Корзины покупок"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "recipe"],
                name="unique_user_recipe_in_shopping_cart"
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
                fields=["user", "author"],
                name="unique_user_author_subscription"
            ),
            models.CheckConstraint(
                check=~models.Q(user=models.F("author")),
                name="prevent_self_follow"
            ),
        ]

    def __str__(self):
        return f"{self.user} {self.author}"


class RecipeShortLink(models.Model):
    recipe = models.ForeignKey(Recipe, verbose_name="Рецепт", on_delete=models.
                               CASCADE)
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
