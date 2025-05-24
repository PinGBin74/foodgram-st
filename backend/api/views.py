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

from django.conf import settings
from .serializers import (
    RecipeSerializer,
    IngredientSerializer,
    AddFavorite,
    UserSerializer,
    FollowSerializer,
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
)


logger = logging.getLogger(__name__)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None


class FollowViewSet(UserViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[IsAuthenticated],
        url_path="subscribe",
    )
    def subscribe(self, request, id=None):
        user = request.user
        author = get_object_or_404(User, id=id)
        if request.method == "POST":
            if user == author:
                return Response(
                    {"errors": "Нельзя подписаться на самого себя!"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if Follow.objects.filter(user=user, author=author).exists():
                return Response(
                    {"errors": "Вы уже подписаны на этого пользователя!"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            Follow.objects.create(user=user, author=author)
            serializer = FollowSerializer(author, context={"request": request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == "DELETE":
            follow = get_object_or_404(Follow, author=author, user=user)
            follow.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated],
        url_path="subscriptions",
    )
    def subscriptions(self, request):
        user = request.user
        queryset = User.objects.filter(following__user=user).prefetch_related("recipes")
        if not queryset:
            return Response(
                "Вы ни на кого не подписаны.", status=status.HTTP_400_BAD_REQUEST
            )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = FollowSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_serializer_context(self):
        """Добавляем request в контекст сериализатора"""

        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[IsAuthenticated],
        url_path="favorite",
    )
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)
        user = request.user
        if request.method == "POST":
            if Favorite.objects.filter(recipe=recipe, user=user).exists():
                return Response(
                    {"error": "Рецепт уже в избранном!"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            Favorite.objects.create(user=user, recipe=recipe)
            serializer = AddFavorite(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == "DELETE":
            favorite = get_object_or_404(Favorite, recipe=recipe, user=user)
            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[IsAuthenticated],
        url_path="shopping_cart",
    )
    def shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)
        user = request.user
        if request.method == "POST":
            if ShoppingCart.objects.filter(recipe=recipe, user=user).exists():
                return Response(
                    {"error": "Рецепт уже добавлен в корзину!"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            ShoppingCart.objects.create(recipe=recipe, user=user)
            serializer = AddFavorite(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == "DELETE":
            recipe = get_object_or_404(ShoppingCart, recipe=recipe, user=user)
            recipe.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=("get",),
        permission_classes=[IsAuthenticated],
        url_path="download_shopping_cart",
    )
    def download_shopping_cart(self, request):
        user_cart = ShoppingCart.objects.filter(user=request.user)
        recipes_ids = user_cart.values_list("recipe_id", flat=True)

        ingredients = (
            RecipeIngredient.objects.filter(recipe_id__in=recipes_ids)
            .values("ingredient__name", "ingredient__measurement_unit")
            .annotate(total_amount=Sum("amount"))
            .order_by("ingredient__name")
        )

        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter="\t")
        writer.writerow(["Список покупок"])
        writer.writerow(["Ингредиенты", "Количетсво", "Ед. измерения"])

        for item in ingredients:
            writer.writerow(
                [
                    item["ingredient__name"],
                    item["total_amount"],
                    item["ingredient__measurement_unit"],
                ]
            )

        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="shopping_list.txt"'
        buffer.close()
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
