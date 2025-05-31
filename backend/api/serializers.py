from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.core.cache import cache

from recipes.serializers import ShortRecipeSerializer, UserSerializer

User = get_user_model()


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
        read_only_fields = ("email", "username")

    def get_recipes(self, obj):
        request = self.context.get("request")
        recipes_limit = request.query_params.get("recipes_limit", "all")
        cache_key = f"user_recipes_{obj.id}_{recipes_limit}"
        cached_recipes = cache.get(cache_key)

        if cached_recipes is not None:
            return cached_recipes

        recipes = obj.recipes.all()
        recipes_limit = request.query_params.get("recipes_limit")

        if recipes_limit and recipes_limit.isdigit():
            recipes = recipes[: int(recipes_limit)]

        serialized_recipes = ShortRecipeSerializer(
            recipes, many=True, context=self.context
        ).data

        # Cache for 1 hour
        cache.set(cache_key, serialized_recipes, 3600)
        return serialized_recipes

    def get_recipes_count(self, obj):
        cache_key = f"user_recipes_count_{obj.id}"
        cached_count = cache.get(cache_key)

        if cached_count is not None:
            return cached_count

        count = obj.recipes.count()
        # Cache for 1 hour
        cache.set(cache_key, count, 3600)
        return count

    def validate(self, data):
        """
        Validate subscription data
        """
        user = self.context["request"].user
        author = self.instance

        if user == author:
            raise serializers.ValidationError(
                "You cannot subscribe to yourself")

        if user.following.filter(id=author.id).exists():
            raise serializers.ValidationError(
                "You are already subscribed to this user"
            )

        return data
