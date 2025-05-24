from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models

User = get_user_model()


class Tag(models.Model):
    """Tag model for recipes."""

    name = models.CharField("Name", max_length=200, unique=True)
    color = models.CharField("Color", max_length=7, unique=True)
    slug = models.SlugField("Slug", max_length=200, unique=True)

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """Ingredient model for recipes."""

    name = models.CharField("Name", max_length=200)
    measurement_unit = models.CharField("Measurement unit", max_length=200)

    class Meta:
        verbose_name = "Ingredient"
        verbose_name_plural = "Ingredients"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "measurement_unit"], name="unique_ingredient"
            )
        ]

    def __str__(self):
        return f"{self.name}, {self.measurement_unit}"


class Recipe(models.Model):
    """Recipe model."""

    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="recipes", verbose_name="Author"
    )
    name = models.CharField("Name", max_length=200)
    image = models.ImageField("Image", upload_to="recipes/")
    text = models.TextField("Description")
    ingredients = models.ManyToManyField(
        Ingredient, through="RecipeIngredient", verbose_name="Ingredients"
    )
    tags = models.ManyToManyField(Tag, verbose_name="Tags")
    cooking_time = models.PositiveSmallIntegerField(
        "Cooking time (minutes)", validators=[MinValueValidator(1)]
    )
    pub_date = models.DateTimeField("Publication date", auto_now_add=True)

    class Meta:
        verbose_name = "Recipe"
        verbose_name_plural = "Recipes"
        ordering = ["-pub_date"]

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    """Model for ingredients in recipes."""

    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, verbose_name="Recipe")
    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.CASCADE, verbose_name="Ingredient"
    )
    amount = models.PositiveSmallIntegerField(
        "Amount", validators=[MinValueValidator(1)]
    )

    class Meta:
        verbose_name = "Recipe ingredient"
        verbose_name_plural = "Recipe ingredients"
        constraints = [
            models.UniqueConstraint(
                fields=["recipe", "ingredient"], name="unique_recipe_ingredient"
            )
        ]


class Favorite(models.Model):
    """Model for favorite recipes."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="favorites", verbose_name="User"
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="favorites",
        verbose_name="Recipe",
    )

    class Meta:
        verbose_name = "Favorite"
        verbose_name_plural = "Favorites"
        constraints = [
            models.UniqueConstraint(fields=["user", "recipe"], name="unique_favorite")
        ]


class ShoppingCart(models.Model):
    """Model for shopping cart."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="shopping_cart",
        verbose_name="User",
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="shopping_cart",
        verbose_name="Recipe",
    )

    class Meta:
        verbose_name = "Shopping cart"
        verbose_name_plural = "Shopping carts"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "recipe"], name="unique_shopping_cart"
            )
        ]
