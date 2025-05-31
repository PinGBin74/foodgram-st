from rest_framework import serializers, status

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
                "Необходимо указать хотя бы один ингредиент"
            )

        ingredient_ids = []
        for ingredient in value:
            if not isinstance(ingredient, dict):
                raise serializers.ValidationError(
                    "Неверный формат ингредиента"
                )
            if "id" not in ingredient or "amount" not in ingredient:
                raise serializers.ValidationError(
                    "Отсутствует id или amount в ингредиенте"
                )
            if ingredient["id"] in ingredient_ids:
                raise serializers.ValidationError(
                    "Ингредиенты не должны повторяться"
                )
            ingredient_ids.append(ingredient["id"])

        return value

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
        except Ingredient.DoesNotExist:
            recipe.delete()
            raise serializers.ValidationError(
                {"errors": "Один или несколько ингредиентов не существуют"},
                code=status.HTTP_400_BAD_REQUEST,
            )
        return recipe

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
            except Ingredient.DoesNotExist:
                raise serializers.ValidationError(
                    {"errors": ERROR_MESSAGES["ingredients_not_exist"]},
                    code=status.HTTP_400_BAD_REQUEST,
                )
        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["ingredients"] = IngredientSerializer(
            instance.ingredients_items.all(), many=True
        ).data
        return representation

    def get_is_favorited(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return Favorite.objects.filter(user=request.user, recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return ShoppingCart.objects.filter(user=request.user,
                                           recipe=obj).exists()


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

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")
