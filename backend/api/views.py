from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
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
        name = self.request.query_params.get("name", "").strip()

        if name:
            queryset = queryset.filter(name__istartswith=name)

        return queryset

    @action(detail=False, methods=["get"])
    def search(self, request):
        """
        Search endpoint for ingredients
        """
        name = request.query_params.get("name", "").strip()
        if not name:
            return Response(
                {"error": "Search parameter 'name' is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


def redirect_by_hash(request, url_hash):
    if not url_hash:
        return Response(
            {"error": "Invalid link format"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        cache_key = f"recipe_hash_{url_hash}"
        recipe_id = cache.get(cache_key)

        if not recipe_id:
            short_link = get_object_or_404(RecipeShortLink, url_hash=url_hash)
            recipe_id = short_link.recipe.id
            # Cache for 24 hours since recipe links are more permanent
            cache.set(cache_key, recipe_id, 86400)

        return redirect(f"{settings.BASE_URL}/api/recipes/{recipe_id}")
    except RecipeShortLink.DoesNotExist:
        logger.error(f"Short link not found for hash: {url_hash}")
        return Response({"error": "Recipe not found"},
                        status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error redirecting hash {url_hash}: {str(e)}")
        return Response(
            {"error": "Internal server error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
