from rest_framework import status, viewsets
from rest_framework.response import Response
from django.shortcuts import get_object_or_404, redirect
from django.conf import settings
from django.core.cache import cache
import logging

from ingredient.serializers import IngredientSimpleSerializer
from recipes.models import (
    Ingredient,
    RecipeShortLink,
)


logger = logging.getLogger(__name__)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSimpleSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = Ingredient.objects.all()
        name = self.request.query_params.get("name")
        if name:
            return queryset.filter(name__istartswith=name)
        return queryset


def redirect_by_hash(request, url_hash):
    try:
        cache_key = f"recipe_hash_{url_hash}"
        recipe_id = cache.get(cache_key)

        if not recipe_id:
            short_link = get_object_or_404(RecipeShortLink, url_hash=url_hash)
            recipe_id = short_link.recipe.id
            cache.set(cache_key, recipe_id, 3600)

        return redirect(f"{settings.BASE_URL}/api/recipes/{recipe_id}")
    except Exception as e:
        logger.error(f"Error redirecting hash {url_hash}: {str(e)}")
        return Response({"error": "Рецепт не найден"},
                        status=status.HTTP_404_NOT_FOUND)
