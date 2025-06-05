from django.core.files.base import ContentFile
import base64
from rest_framework import serializers

from ingredient.models import Ingredient
from ingredient.serializers import IngredientSerializer
from users.serializers import CustomUserSerializer
from .models import Recipe, RecipeIngredient, Favorite, ShoppingCart


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith("data:image"):
            format, imgstr = data.split(";base64,")
            ext = format.split("/")[-1]
            data = ContentFile(base64.b64decode(imgstr), name=f"image.{ext}")
        return super().to_internal_value(data)


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="ingredient.id")
    name = serializers.CharField(source="ingredient.name", read_only=True)
    measurement_unit = serializers.CharField(
        source="ingredient.measurement_unit", read_only=True
    )
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ("id", "name", "measurement_unit", "amount")


class RecipeSerializer(serializers.ModelSerializer):
    author = CustomUserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(source="recipe_ingredients", many=True)
    image = Base64ImageField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            "id",
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
        if request and request.user.is_authenticated:
            return Favorite.objects.filter(user=request.user, recipe=obj).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return ShoppingCart.objects.filter(user=request.user, recipe=obj).exists()
        return False

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError(
                "Необходимо указать хотя бы один ингредиент."
            )
        ingredient_ids = [item["ingredient"]["id"] for item in value]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError("Ингредиенты не должны повторяться.")
        for item in value:
            if not Ingredient.objects.filter(id=item["ingredient"]["id"]).exists():
                raise serializers.ValidationError(
                    f'Ингредиент с id {item["ingredient"]["id"]} не существует.'
                )
        return value

    def create_ingredients(self, recipe, ingredients_data):
        recipe_ingredients = [
            RecipeIngredient(
                recipe=recipe,
                ingredient=Ingredient.objects.get(id=item["ingredient"]["id"]),
                amount=item["amount"],
            )
            for item in ingredients_data
        ]
        RecipeIngredient.objects.bulk_create(recipe_ingredients)

    def create(self, validated_data):
        ingredients_data = validated_data.pop("recipe_ingredients")
        recipe = Recipe.objects.create(
            author=self.context["request"].user, **validated_data
        )
        self.create_ingredients(recipe, ingredients_data)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop("recipe_ingredients", None)
        instance = super().update(instance, validated_data)
        if ingredients_data:
            instance.recipe_ingredients.all().delete()
            self.create_ingredients(instance, ingredients_data)
        return instance
