from django.contrib.auth import get_user_model
from djoser.serializers import UserCreateSerializer, UserSerializer
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Tag,
    Subscription,
)
from .fields import Base64ImageField

User = get_user_model()


class CustomUserCreateSerializer(UserCreateSerializer):
    """Serializer for user creation."""

    class Meta:
        model = User
        fields = (
            "email",
            "id",
            "username",
            "first_name",
            "last_name",
            "password",
        )


class CustomUserSerializer(UserSerializer):
    """Serializer for user model."""

    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "email",
            "id",
            "username",
            "first_name",
            "last_name",
            "is_subscribed",
            "recipes",
            "recipes_count",
        )

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        if request is None or request.user.is_anonymous:
            return False
        return Subscription.objects.filter(user=request.user, author=obj).exists()

    def get_recipes(self, obj):
        request = self.context.get("request")
        recipes = obj.recipes.all()
        if request and request.query_params.get("recipes_limit"):
            try:
                limit = int(request.query_params.get("recipes_limit"))
                recipes = recipes[:limit]
            except ValueError:
                pass
        return RecipeSerializer(recipes, many=True, context=self.context).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()


class TagSerializer(serializers.ModelSerializer):
    """Serializer for tag model."""

    class Meta:
        model = Tag
        fields = ("id", "name", "color", "slug")


class IngredientSerializer(serializers.ModelSerializer):
    """Serializer for ingredient model."""

    class Meta:
        model = Ingredient
        fields = ("id", "name", "measurement_unit")


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Serializer for recipe ingredients."""

    id = serializers.ReadOnlyField(source="ingredient.id")
    name = serializers.ReadOnlyField(source="ingredient.name")
    measurement_unit = serializers.ReadOnlyField(source="ingredient.measurement_unit")

    class Meta:
        model = RecipeIngredient
        fields = ("id", "name", "measurement_unit", "amount")


class RecipeSerializer(serializers.ModelSerializer):
    """Serializer for recipe model."""

    tags = TagSerializer(many=True, read_only=True)
    author = CustomUserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        source="recipeingredient_set",
        many=True,
        read_only=True,
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            "id",
            "tags",
            "author",
            "ingredients",
            "is_favorited",
            "is_in_shopping_cart",
            "name",
            "image",
            "text",
            "cooking_time",
        )

    def get_is_favorited(self, obj):
        request = self.context.get("request")
        if request is None or request.user.is_anonymous:
            return False
        return Favorite.objects.filter(user=request.user, recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get("request")
        if request is None or request.user.is_anonymous:
            return False
        return ShoppingCart.objects.filter(user=request.user, recipe=obj).exists()


class RecipeIngredientCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating recipe ingredients."""

    id = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ("id", "amount")


class RecipeCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating recipes."""

    ingredients = RecipeIngredientCreateSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
    )
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            "ingredients",
            "tags",
            "image",
            "name",
            "text",
            "cooking_time",
        )

    def create(self, validated_data):
        ingredients_data = validated_data.pop("ingredients")
        tags_data = validated_data.pop("tags")
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)
        for ingredient_data in ingredients_data:
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient_id=ingredient_data["id"],
                amount=ingredient_data["amount"],
            )
        return recipe

    def update(self, instance, validated_data):
        if "ingredients" in validated_data:
            ingredients_data = validated_data.pop("ingredients")
            instance.ingredients.clear()
            for ingredient_data in ingredients_data:
                RecipeIngredient.objects.create(
                    recipe=instance,
                    ingredient_id=ingredient_data["id"],
                    amount=ingredient_data["amount"],
                )
        if "tags" in validated_data:
            tags_data = validated_data.pop("tags")
            instance.tags.set(tags_data)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class FavoriteSerializer(serializers.ModelSerializer):
    """Serializer for favorite recipes."""

    class Meta:
        model = Favorite
        fields = ("user", "recipe")
        validators = [
            UniqueTogetherValidator(
                queryset=Favorite.objects.all(),
                fields=("user", "recipe"),
                message="Recipe is already in favorites.",
            )
        ]


class ShoppingCartSerializer(serializers.ModelSerializer):
    """Serializer for shopping cart."""

    class Meta:
        model = ShoppingCart
        fields = ("user", "recipe")
        validators = [
            UniqueTogetherValidator(
                queryset=ShoppingCart.objects.all(),
                fields=("user", "recipe"),
                message="Recipe is already in shopping cart.",
            )
        ]
