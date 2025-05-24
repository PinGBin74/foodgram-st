from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Sum
from djoser.views import UserViewSet
import csv
import io
import hashlib
import base64
from django.core.cache import cache
import logging
from django.contrib.auth import get_user_model

from django.conf import settings
from .serializers import (
    RecipeSerializer,
    IngredientSerializer,
    AddFavorite,
    UserSerializer,
    FollowSerializer,
    CustomUserSerializer,
    TagSerializer,
)
from recipes.models import (
    Recipe,
    Ingredient,
    Favorite,
    ShoppingCart,
    RecipeIngredient,
    RecipeShortLink,
    User,
    Follow,
    Tag,
)
from .filters import IngredientFilter, RecipeFilter
from .permissions import IsAuthorOrReadOnly


logger = logging.getLogger(__name__)

User = get_user_model()


class CustomUserViewSet(UserViewSet):
    """ViewSet for user model."""

    queryset = User.objects.all()
    serializer_class = CustomUserSerializer

    @action(
        detail=True, methods=["post", "delete"], permission_classes=[IsAuthenticated]
    )
    def subscribe(self, request, id):
        user = request.user
        author = get_object_or_404(User, id=id)

        if request.method == "POST":
            if user == author:
                return Response(
                    {"error": "You cannot subscribe to yourself."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if user.follower.filter(author=author).exists():
                return Response(
                    {"error": "You are already subscribed to this user."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user.follower.create(author=author)
            serializer = self.get_serializer(author)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == "DELETE":
            if not user.follower.filter(author=author).exists():
                return Response(
                    {"error": "You are not subscribed to this user."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user.follower.filter(author=author).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        user = request.user
        queryset = User.objects.filter(following__user=user)
        pages = self.paginate_queryset(queryset)
        serializer = self.get_serializer(pages, many=True)
        return self.get_paginated_response(serializer.data)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for tag model."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for ingredient model."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filterset_class = IngredientFilter
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    """ViewSet for recipe model."""

    queryset = Recipe.objects.all()
    permission_classes = (IsAuthorOrReadOnly,)
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ("create", "partial_update"):
            return RecipeCreateSerializer
        return RecipeSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(
        detail=True, methods=["post", "delete"], permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk):
        return self._handle_recipe_action(request, pk, Favorite, "favorites")

    @action(
        detail=True, methods=["post", "delete"], permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk):
        return self._handle_recipe_action(request, pk, ShoppingCart, "shopping_cart")

    def _handle_recipe_action(self, request, pk, model, related_name):
        user = request.user
        recipe = get_object_or_404(Recipe, pk=pk)

        if request.method == "POST":
            if getattr(user, related_name).filter(recipe=recipe).exists():
                return Response(
                    {"error": f"Recipe is already in {related_name}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            model.objects.create(user=user, recipe=recipe)
            serializer = RecipeSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == "DELETE":
            if not getattr(user, related_name).filter(recipe=recipe).exists():
                return Response(
                    {"error": f"Recipe is not in {related_name}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            getattr(user, related_name).filter(recipe=recipe).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        user = request.user
        ingredients = (
            RecipeIngredient.objects.filter(recipe__shopping_cart__user=user)
            .values("ingredient__name", "ingredient__measurement_unit")
            .annotate(amount=Sum("amount"))
        )

        shopping_list = ["Shopping List:\n"]
        for ingredient in ingredients:
            shopping_list.append(
                f'{ingredient["ingredient__name"]} - '
                f'{ingredient["amount"]} '
                f'{ingredient["ingredient__measurement_unit"]}\n'
            )

        response = HttpResponse("".join(shopping_list), content_type="text/plain")
        response["Content-Disposition"] = 'attachment; filename="shopping_list.txt"'
        return response

    @action(detail=True, methods=["get"], url_path="get_link")
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        hash_input = f"{recipe.id}{recipe.name}{recipe.created_at}"
        url_hash = self.generate_hash(hash_input)

        short_link, created = RecipeShortLink.objects.get_or_create(
            recipe=recipe, defaults={"url_hash": url_hash}
        )

        short_url = f"{settings.BASE_URL}/a/r/{short_link.url_hash}"
        return Response({"short_link": short_url})

    def generate_hash(self, input_str):
        """Генерация 8-символьного хэша"""
        # Создание хэша в формате SHA256
        hash_bytes = hashlib.sha256(input_str.encode()).digest()
        # Кодируем в base64 и берем первые 8 символов
        return base64.urlsafe_b64encode(hash_bytes).decode()[:8]


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
        return Response(status=status.HTTP_404_NOT_FOUND)
