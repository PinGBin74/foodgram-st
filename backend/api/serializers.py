import base64
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from djoser.serializers import UserSerializer as BaseUserSerializer
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.validators import UniqueTogetherValidator

from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Follow,
)


User = get_user_model()

ALLOWED_IMAGE_FORMATS = ["jpeg", "jpg", "png", "gif"]

ERROR_MESSAGES = {
    "invalid_base64": "Некорректный формат base64 изображения",
    "invalid_image_format": "Неподдерживаемый формат изображения",
    "invalid_base64_data": "Некорректные base64 данные",
    "ingredient_not_found": "Ингредиент с указанным id не существует",
    "ingredient_duplicate": "Ингредиенты не должны повторяться",
    "no_ingredients": "Необходимо указать хотя бы один ингредиент",
    "empty_ingredients": "Список ингредиентов не может быть пустым",
}


class Base64ImageField(serializers.ImageField):
    """Поле для кодирования/декодирования изображения Base64"""

    def to_internal_value(self, data):
        try:
            if isinstance(data, str) and data.startswith("data:image"):
                parts = data.split(";base64,")
                if len(parts) != 2:
                    raise serializers.ValidationError(ERROR_MESSAGES["invalid_base64"])

                format_part = parts[0]
                imgstr = parts[1]

                ext = format_part.split("/")[-1]
                if ext not in ALLOWED_IMAGE_FORMATS:
                    raise serializers.ValidationError(
                        ERROR_MESSAGES["invalid_image_format"]
                    )

                try:
                    decoded_file = base64.b64decode(imgstr)
                except (TypeError, binascii.Error):
                    raise serializers.ValidationError(
                        ERROR_MESSAGES["invalid_base64_data"]
                    )

                data = ContentFile(decoded_file, name=f"photo.{ext}")

            return super().to_internal_value(data)

        except Exception as e:
            raise serializers.ValidationError(str(e))


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ("id", "name", "measurement_unit")


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source="ingredient.id")
    name = serializers.ReadOnlyField(source="ingredient.name")
    measurement_unit = serializers.ReadOnlyField(source="ingredient.measurement_unit")

    class Meta:
        model = RecipeIngredient
        fields = ("id", "name", "measurement_unit", "amount")


class UserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField(required=False)

    class Meta:
        model = User
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "username",
            "is_subscribed",
            "avatar",
        )

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return Follow.objects.filter(user=request.user, author=obj).exists()


"""
class CreateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'password')
        extra_kwargs = {
            'password': {'write_only': True},
            'username': {
                'validators': [AllowedCharactersUsernameValidator()]
            }
        }

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            password=validated_data['password']
        )
        return user
"""


class ShortRecipeSerializer(serializers.ModelSerializer):
    """Укороченный сериализатор для рецептов в подписках"""

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")


class FollowSerializer(UserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "username",
            "is_subscribed",
            "avatar",
            "recipes",
            "recipes_count",
        )

    def get_recipes(self, obj):
        request = self.context.get("request")
        recipes = obj.recipes.all()

        recipes_limit = request.query_params.get("recipes_limit")
        if recipes_limit and recipes_limit.isdigit():
            recipes = recipes[: int(recipes_limit)]

        return ShortRecipeSerializer(recipes, many=True, context=self.context).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()


class RecipeIngredientCreateSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    amount = serializers.IntegerField(min_value=1)

    def validate_id(self, value):
        try:
            Ingredient.objects.get(id=value)
        except Ingredient.DoesNotExist:
            raise serializers.ValidationError(ERROR_MESSAGES["ingredient_not_found"])
        return value


class RecipeSerializer(serializers.ModelSerializer):
    image = Base64ImageField()
    author = UserSerializer(read_only=True)
    ingredients = RecipeIngredientCreateSerializer(many=True, write_only=True)
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
        if self.context["request"].method in ["POST", "PATCH", "PUT"]:
            if "ingredients" not in self.initial_data:
                raise serializers.ValidationError(
                    {"errors": ERROR_MESSAGES["no_ingredients"]},
                    code=status.HTTP_400_BAD_REQUEST,
                )
            if not self.initial_data.get("ingredients"):
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
            if ingredient["id"] in ingredient_ids:
                raise serializers.ValidationError("Ингредиенты не должны повторяться")
            ingredient_ids.append(ingredient["id"])

        return value

    def create(self, validated_data):
        ingredients_data = validated_data.pop("ingredients")
        recipe = Recipe.objects.create(**validated_data)

        recipe_ingredients = [
            RecipeIngredient(
                recipe=recipe,
                ingredient=Ingredient.objects.get(id=ingredient_data["id"]),
                amount=ingredient_data["amount"],
            )
            for ingredient_data in ingredients_data
        ]

        RecipeIngredient.objects.bulk_create(recipe_ingredients)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop("ingredients", None)
        instance.name = validated_data.get("name", instance.name)
        instance.text = validated_data.get("text", instance.text)
        instance.cooking_time = validated_data.get(
            "cooking_time", instance.cooking_time
        )

        if "image" in validated_data:
            instance.image = validated_data.get("image", instance.image)
        instance.save()

        if ingredients_data is not None:
            instance.ingredients_items.all().delete()
            recipe_ingredients = [
                RecipeIngredient(
                    recipe=instance,
                    ingredient=Ingredient.objects.get(id=ingredient_data["id"]),
                    amount=ingredient_data["amount"],
                )
                for ingredient_data in ingredients_data
            ]
            RecipeIngredient.objects.bulk_create(recipe_ingredients)
        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["ingredients"] = RecipeIngredientSerializer(
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
        return ShoppingCart.objects.filter(user=request.user, recipe=obj).exists()


class AddFavorite(serializers.ModelSerializer):
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")


class AddAvatar(serializers.ModelSerializer):
    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = ("avatar",)
