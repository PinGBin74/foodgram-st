from rest_framework import serializers
from recipes.models import (
    RecipeIngredient,
    Ingredient,
)


class CreateIngredientSerializer(serializers.Serializer):
    id = serializers.IntegerField(min_value=1)
    amount = serializers.IntegerField(min_value=1)

    def validate_id(self, value):
        if not Ingredient.objects.filter(id=value).exists():
            raise serializers.ValidationError(
                "Ингредиент с указанным id не существует"
            )
        return value


class IngredientSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source="ingredient.id")
    name = serializers.ReadOnlyField(source="ingredient.name")
    measurement_unit = serializers.ReadOnlyField(
        source="ingredient.measurement_unit"
    )

    class Meta:
        model = RecipeIngredient
        fields = (
            "id",
            "name",
            "measurement_unit",
            "amount",
        )


class IngredientSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ("id", "name", "measurement_unit")
