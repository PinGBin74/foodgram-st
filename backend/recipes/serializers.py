from rest_framework import serializers, status
from django.core.cache import cache
from django.db import transaction

from const.photo import ImageField
from users.serializers import UserSerializer
from const.errors import ERROR_MESSAGES
from ingredient.serializers import (
    CreateIngredientSerializer,
    IngredientSerializer,
)
from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    User,
)


class RecipeSerializer(serializers.ModelSerializer):
    image = ImageField()
    author = UserSerializer(read_only=True)
    ingredients = CreateIngredientSerializer(many=True, write_only=True)
    cooking_time = serializers.IntegerField(min_value=1)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            "id",
            "name",
            "author",
            "text",
            "image",
            "ingredients",
            "cooking_time",
            "is_favorited",
            "is_in_shopping_cart",
        )

    def validate(self, data):
        request = self.context.get("request")
        if request and request.method in ["POST", "PATCH", "PUT"]:
            ingredients = self.initial_data.get("ingredients")
            if ingredients is None:
                raise serializers.ValidationError(
                    {"errors": ERROR_MESSAGES["no_ingredients"]},
                    code=status.HTTP_400_BAD_REQUEST,
                )
            if not ingredients:
                raise serializers.ValidationError(
                    {"errors": ERROR_MESSAGES["empty_ingredients"]},
                    code=status.HTTP_400_BAD_REQUEST,
                )
        return data

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError(
                "At least one ingredient is required",
                code=status.HTTP_400_BAD_REQUEST,
            )

        ingredient_ids = []
        for ingredient in value:
            if not isinstance(ingredient, dict):
                raise serializers.ValidationError("Invalid ingredient format")
            if "id" not in ingredient or "amount" not in ingredient:
                raise serializers.ValidationError(
                    "Missing id or amount in ingredient")
            if ingredient["id"] in ingredient_ids:
                raise serializers.ValidationError(
                    "Duplicate ingredients are not allowed"
                )
            ingredient_ids.append(ingredient["id"])

        return value

    def _invalidate_recipe_caches(self, recipe_id):
        """Invalidate all caches related to a specific recipe."""
        cache.delete(f"recipe_{recipe_id}")
        cache.delete("recipes_list_")

    @transaction.atomic
    def create(self, validated_data):
        ingredients_data = validated_data.pop("ingredients", [])
        recipe = Recipe.objects.create(**validated_data)

        try:
            recipe_ingredients = []
            for ingredient_data in ingredients_data:
                ingredient = Ingredient.objects.get(id=ingredient_data["id"])
                recipe_ingredients.append(
                    RecipeIngredient(
                        recipe=recipe,
                        ingredient=ingredient,
                        amount=ingredient_data["amount"],
                    )
                )
            RecipeIngredient.objects.bulk_create(recipe_ingredients)

            # Invalidate cache
            self._invalidate_recipe_caches(recipe.id)

            return recipe
        except Ingredient.DoesNotExist:
            recipe.delete()
            raise serializers.ValidationError(
                {"errors": "One or more ingredients do not exist"},
                code=status.HTTP_400_BAD_REQUEST,
            )

    @transaction.atomic
    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop("ingredients", None)

        # Update basic fields
        for field in ["name", "text", "cooking_time"]:
            if field in validated_data:
                setattr(instance, field, validated_data[field])

        if "image" in validated_data:
            instance.image = validated_data["image"]
        instance.save()

        # Update ingredients if provided
        if ingredients_data is not None:
            instance.ingredients_items.all().delete()
            try:
                recipe_ingredients = []
                for ingredient_data in ingredients_data:
                    ingredient = Ingredient.objects.get(
                        id=ingredient_data["id"])
                    recipe_ingredients.append(
                        RecipeIngredient(
                            recipe=instance,
                            ingredient=ingredient,
                            amount=ingredient_data["amount"],
                        )
                    )
                RecipeIngredient.objects.bulk_create(recipe_ingredients)

                # Invalidate cache
                self._invalidate_recipe_caches(instance.id)

            except Ingredient.DoesNotExist:
                raise serializers.ValidationError(
                    {"errors": ERROR_MESSAGES["ingredients_not_exist"]},
                    code=status.HTTP_400_BAD_REQUEST,
                )
        return instance

    def to_representation(self, instance):
        cache_key = f"recipe_{instance.id}"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return cached_data

        representation = super().to_representation(instance)
        representation["ingredients"] = IngredientSerializer(
            instance.ingredients_items.all(), many=True
        ).data

        # Cache for 1 hour
        cache.set(cache_key, representation, 3600)
        return representation

    def get_is_favorited(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False

        cache_key = f"recipe_favorite_{obj.id}_{request.user.id}"
        cached_value = cache.get(cache_key)

        if cached_value is not None:
            return cached_value

        is_favorited = Favorite.objects.filter(
            user=request.user, recipe=obj).exists()

        # Cache for 1 hour
        cache.set(cache_key, is_favorited, 3600)
        return is_favorited

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False

        cache_key = f"recipe_cart_{obj.id}_{request.user.id}"
        cached_value = cache.get(cache_key)

        if cached_value is not None:
            return cached_value

        is_in_cart = ShoppingCart.objects.filter(
            user=request.user, recipe=obj).exists()

        # Cache for 1 hour
        cache.set(cache_key, is_in_cart, 3600)
        return is_in_cart


class AddFavorite(serializers.ModelSerializer):
    image = ImageField()

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")


class AddAvatar(serializers.ModelSerializer):
    avatar = ImageField(required=True)

    class Meta:
        model = User
        fields = ("avatar",)


class ShortRecipeSerializer(serializers.ModelSerializer):
    image = ImageField()
    short_link = serializers.SerializerMethodField(source="get_short_link")

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time", "short_link")

    def get_short_link(self, obj):
        request = self.context.get("request")
        if not request:
            return None
        return request.build_absolute_uri(f"/recipes/{obj.id}")

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["short-link"] = representation.pop("short_link")
        return representation
