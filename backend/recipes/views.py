from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import (IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.conf import settings
from django.core.cache import cache
import csv
import io
import hashlib
import base64
import logging

from const.errors import ERRORS


from .serializers import (
    RecipeSerializer,
    AddFavorite,
)
from recipes.models import (
    Recipe,
    Favorite,
    ShoppingCart,
    RecipeIngredient,
    RecipeShortLink,
)


logger = logging.getLogger(__name__)


class RecipeViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с рецептами.

    Предоставляет CRUD операции для рецептов, а также дополнительные действия
    для работы с избранным, списком покупок и генерации коротких ссылок.
    """
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = LimitOffsetPagination

    def perform_create(self, serializer):
        """Создает новый рецепт и
        устанавливает текущего пользователя как автора.
        """
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        """Обновляет рецепт, проверяя права доступа автора."""
        if serializer.instance.author != self.request.user:
            raise PermissionDenied(detail=ERRORS["cant_edit"])
        serializer.save()

    def perform_destroy(self, instance):
        """Удаляет рецепт, проверяя права доступа автора."""
        if instance.author != self.request.user:
            raise PermissionDenied(detail=ERRORS["cant_delete"])
        instance.delete()

    def get_serializer_context(self):
        """Добавляет request в контекст
        сериализатора для доступа к текущему пользователю.
        """
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def get_queryset(self):
        """Возвращает отфильтрованный список рецептов.
        Поддерживает фильтрацию по автору,
        наличию в избранном и списке покупок.
        """
        queryset = Recipe.objects.select_related("author").prefetch_related(
            "ingredients"
        )

        if not self.request.user.is_authenticated:
            return queryset

        filters = {}
        author = self.request.query_params.get("author")
        is_in_shopping_cart = self.request.query_params.get(
            "is_in_shopping_cart")
        is_favorited = self.request.query_params.get("is_favorited")

        if author:
            filters["author_id"] = author
        if is_in_shopping_cart:
            filters["shoppingcart__user"] = self.request.user
        if is_favorited:
            filters["favorite__user"] = self.request.user

        return queryset.filter(**filters).distinct()

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[IsAuthenticated],
        url_path="favorite",
    )
    def favorite(self, request, pk=None):
        """Добавляет или удаляет рецепт из избранного пользователя."""
        recipe = get_object_or_404(Recipe, id=pk)
        user = request.user
        if request.method == "POST":
            if Favorite.objects.filter(recipe=recipe, user=user).exists():
                return Response(
                    {"error": ERRORS["already_in_favorites"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            Favorite.objects.create(user=user, recipe=recipe)
            serializer = AddFavorite(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == "DELETE":
            favorite = Favorite.objects.filter(recipe=recipe, user=user)
            if not favorite.exists():
                return Response(
                    {"errors": ERRORS["not_in_favorites"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(
            {"error": "Метод не разрешен"}, status=status.
            HTTP_405_METHOD_NOT_ALLOWED
        )

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[IsAuthenticated],
        url_path="shopping_cart",
    )
    def shopping_cart(self, request, pk=None):
        """Добавляет или удаляет рецепт из списка покупок пользователя."""
        recipe = get_object_or_404(Recipe, id=pk)
        user = request.user

        if request.method == "POST":
            if ShoppingCart.objects.filter(recipe=recipe, user=user).exists():
                return Response(
                    {"error": ERRORS["already_in_cart"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            ShoppingCart.objects.create(user=user, recipe=recipe)
            serializer = AddFavorite(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == "DELETE":
            shopping_cart = ShoppingCart.objects.filter(recipe=recipe,
                                                        user=user)
            if not shopping_cart.exists():
                return Response(
                    {"errors": ERRORS["not_in_cart"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            shopping_cart.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(
            {"error": "Метод не разрешен"}, status=status.
            HTTP_405_METHOD_NOT_ALLOWED
        )

    @action(
        detail=False,
        methods=("get",),
        permission_classes=[IsAuthenticated],
        url_path="download_shopping_cart",
    )
    def download_shopping_cart(self, request):
        """Скачивает список покупок пользователя в формате CSV.

        Список содержит все ингредиенты из рецептов в корзине покупок,
        сгруппированные по названию и суммированные по количеству.
        """
        user = request.user
        cache_key = f"shopping_cart_{user.id}"
        cached_data = cache.get(cache_key)

        if cached_data:
            response = HttpResponse(cached_data, content_type="text/csv")
            response["Content-Disposition"] = (
                'attachment; filename="shopping_list.txt"'
            )
            return response

        try:
            ingredients = (
                RecipeIngredient.objects.filter(
                    recipe__shoppingcart__user=user)
                .values("ingredient__name", "ingredient__measurement_unit")
                .annotate(total_amount=Sum("amount"))
                .order_by("ingredient__name")
            )

            if not ingredients.exists():
                return Response(
                    {"error": "Список покупок пуст"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            buffer = io.StringIO()
            writer = csv.writer(buffer, delimiter="\t")
            writer.writerow(["Список покупок"])
            writer.writerow(["Ингредиенты", "Количество", "Ед. измерения"])

            for item in ingredients:
                writer.writerow([
                    item["ingredient__name"],
                    item["total_amount"],
                    item["ingredient__measurement_unit"],
                ])

            content = buffer.getvalue()
            buffer.close()

            cache.set(cache_key, content, 300)  # кэшируем на 5 минут

            response = HttpResponse(content, content_type="text/csv")
            response["Content-Disposition"] = (
                'attachment; filename="shopping_list.txt"'
            )
            return response

        except Exception as e:
            logger.error(f"Error generating shopping cart: {str(e)}")
            return Response(
                {"error": "Ошибка при формировании списка покупок"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["get"], url_path="get-link")
    def get_link(self, request, pk=None):
        """Генерирует короткую ссылку для рецепта."""
        recipe = self.get_object()
        hash_input = f"{recipe.id}{recipe.name}{recipe.created_at}"
        url_hash = self.generate_hash(hash_input)

        try:
            short_link, created = RecipeShortLink.objects.get_or_create(
                recipe=recipe, defaults={"url_hash": url_hash}
            )

            short_url = f"{settings.BASE_URL}/a/r/{short_link.url_hash}"
            return Response({"short-link": short_url})
        except Exception as e:
            logger.error(f"Error generating short link: {str(e)}")
            return Response(
                {"error": "Ошибка при создании короткой ссылки"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def generate_hash(self, input_str):
        """Генерирует 8-символьный хэш из входной строки.

        Использует SHA256 для создания хэша и кодирует его в base64.
        """
        # Создание хэша в формате SHA256
        hash_bytes = hashlib.sha256(input_str.encode()).digest()
        # Кодируем в base64 и берем первые 8 символов
        return base64.urlsafe_b64encode(hash_bytes).decode()[:8]
