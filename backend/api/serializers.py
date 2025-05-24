import base64
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from recipes.models import Recipe, Ingredient, RecipeIngredient, Follow


User = get_user_model()


class Base64ImageField(serializers.ImageField):
    """Поле для кодирования/декодирования изображения Base64"""

    def to_internal_value(self, data):
        try:
            if isinstance(data, str) and data.startswith("data:image"):
                parts = data.split(";base64,")
                if len(parts) != 2:
                    raise serializers.ValidationError(
                        "Некорректный формат base64 изображения"
                    )

                format_part = parts[0]
                imgstr = parts[1]

                ext = format_part.split("/")[-1]
                if ext not in ["jpeg", "jpg", "png", "gif"]:
                    raise serializers.ValidationError(
                        "Неподдерживаемый формат изображения"
                    )

                try:
                    decoded_file = base64.b64decode(imgstr)
                except (TypeError, binascii.Error):
                    raise serializers.ValidationError("Некорректные base64 данные")

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


class CreateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("email", "id", "username", "first_name", "last_name", "password")
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data["email"],
            username=validated_data["username"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            password=validated_data["password"],
        )
        return user


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


class RecipeSerializer(serializers.ModelSerializer):
    image = Base64ImageField()
    author = UserSerializer(read_only=True)
    ingredients = RecipeIngredientCreateSerializer(many=True, write_only=True)
    cooking_time = serializers.IntegerField(min_value=1)

    class Meta:
        model = Recipe
        fields = (
            "id",
            "name",
            "author",
            "description",
            "image",
            "ingredients",
            "cooking_time",
        )

    def create(self, validated_data):
        ingredients_data = validated_data.pop("ingredients")
        recipe = Recipe.objects.create(**validated_data)

        recipe_ingredients = [
            RecipeIngredient(
                recipe=recipe,
                ingredient_id=ingredient_data["id"],
                amount=ingredient_data["amount"],
            )
            for ingredient_data in ingredients_data
        ]

        RecipeIngredient.objects.bulk_create(recipe_ingredients)
        return recipe

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["ingredients"] = RecipeIngredientSerializer(
            instance.ingredients_items.all(), many=True
        ).data
        return representation

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop("ingredients", None)
        instance.name = validated_data.get("name", instance.name)
        instance.description = validated_data.get("description", instance.description)
        instance.cooking_time = validated_data.get(
            "cooking_time", instance.cooking_time
        )

        if "image" in validated_data:
            instance.image = validated_data.get("image", instance.image)
        instance.save()

        if ingredients_data is not None:
            instance.ingredients_items.all().delete()
            recipe_ingredients = []
            for ingredient_data in ingredients_data:
                try:
                    ingredient = Ingredient.objects.get(id=ingredient_data["id"])
                    recipe_ingredients.append(
                        RecipeIngredient(
                            recipe=instance,
                            ingredient=ingredient,
                            amount=ingredient_data["amount"],
                        )
                    )
                except Ingredient.DoesNotExist:
                    raise serializers.ValidationError(
                        {
                            "ingredients": f'Ингредиент с id {ingredient_data["id"]} не существует'
                        }
                    )
            RecipeIngredient.objects.bulk_create(recipe_ingredients)
        return instance


class AddFavorite(serializers.ModelSerializer):
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")
