from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly
)
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Sum
from django.conf import settings
from django.core.cache import cache
from djoser.views import UserViewSet
import csv
import io
import hashlib
import base64
import logging

from .serializers import (
    RecipeSerializer,
    IngredientSerializer,
    AddFavorite,
    UserSerializer,
    FollowSerializer,
    AddAvatar,
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


ERRORS = {
    "self_subscribe": "Нельзя подписаться на самого себя!",
    "already_subscribed": "Вы уже подписаны на этого пользователя!",
    "not_subscribed": "Вы не подписаны на этого пользователя!",
    "already_in_favorites": "Рецепт уже в избранном!",
    "not_in_favorites": "Рецепт не в избранном!",
    "already_in_cart": "Рецепт уже добавлен в корзину!",
    "not_in_cart": "Рецепт не в корзине!",
    "no_subscriptions": "Вы ни на кого не подписаны.",
    "no_image": "Необходимо загрузить изображение",
    "cant_edit": "Вы не можете изменять чужие рецепты",
    "cant_delete": "Вы не можете удалять чужие рецепты",
}


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = Ingredient.objects.all()
        name = self.request.query_params.get("name")
        if name:
            return queryset.filter(name__istartswith=name)
        return queryset


class FollowViewSet(UserViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = LimitOffsetPagination

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
                    {"errors": ERRORS["self_subscribe"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if Follow.objects.filter(user=user, author=author).exists():
                return Response(
                    {"errors": ERRORS["already_subscribed"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            Follow.objects.create(user=user, author=author)
            serializer = FollowSerializer(author, context={"request": request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == "DELETE":
            follow = Follow.objects.filter(author=author, user=user)
            if not follow.exists():
                return Response(
                    {"errors": ERRORS["not_subscribed"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            follow.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(
            {"error": "Метод не разрешен"},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated],
        url_path="subscriptions",
    )
    def subscriptions(self, request):
        user = request.user
        queryset = User.objects.filter(
            following__user=user
        ).prefetch_related("recipes")
        if not queryset:
            return Response(
                ERRORS["no_subscriptions"], status=status.HTTP_400_BAD_REQUEST
            )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = FollowSerializer(
            page,
            many=True,
            context={"request": request}
        )
        return paginator.get_paginated_response(serializer.data)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated]
    )
    def me(self, request):
        serializer = UserSerializer(request.user, context={"request": request})
        return Response(serializer.data)

    @action(
        detail=False,
        methods=["get", "put", "patch", "delete"],
        permission_classes=[IsAuthenticated],
        url_path="me/avatar",
    )
    def avatar(self, request):
        user = request.user
        if request.method == "GET":
            serializer = UserSerializer(user, context={"request": request})
            return Response(serializer.data)

        if request.method in ["PUT", "PATCH"]:
            if "avatar" not in request.data:
                return Response(
                    {"errors": ERRORS["no_image"]},
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer = AddAvatar(user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        if request.method == "DELETE":
            user.avatar = None
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(
            {"error": "Метод не разрешен"},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = LimitOffsetPagination

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        if serializer.instance.author != self.request.user:
            raise PermissionDenied(detail=ERRORS["cant_edit"])
        serializer.save()

    def perform_destroy(self, instance):
        if instance.author != self.request.user:
            raise PermissionDenied(detail=ERRORS["cant_delete"])
        instance.delete()

    def get_serializer_context(self):
        """Добавляем request в контекст сериализатора"""
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def get_queryset(self):
        queryset = Recipe.objects.select_related("author").prefetch_related(
            "ingredients"
        )

        filters = {}
        if self.request.user.is_authenticated:
            author = self.request.query_params.get("author")
            is_in_shopping_cart = self.request.query_params.get(
                "is_in_shopping_cart"
            )
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
            {"error": "Метод не разрешен"},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

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
                    {"error": ERRORS["already_in_cart"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            ShoppingCart.objects.create(user=user, recipe=recipe)
            serializer = AddFavorite(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == "DELETE":
            shopping_cart = ShoppingCart.objects.filter(
                recipe=recipe,
                user=user
            )
            if not shopping_cart.exists():
                return Response(
                    {"errors": ERRORS["not_in_cart"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            shopping_cart.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(
            {"error": "Метод не разрешен"},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    @action(
        detail=False,
        methods=("get",),
        permission_classes=[IsAuthenticated],
        url_path="download_shopping_cart",
    )
    def download_shopping_cart(self, request):
        user = request.user
        cache_key = f"shopping_cart_{user.id}"
        cached_data = cache.get(cache_key)

        if cached_data:
            response = HttpResponse(cached_data, content_type="text/csv")
            response["Content-Disposition"] = '''
                attachment; filename="shopping_list.txt"
            '''
            return response

        ingredients = (
            RecipeIngredient.objects.filter(recipe__shoppingcart__user=user)
            .values("ingredient__name", "ingredient__measurement_unit")
            .annotate(total_amount=Sum("amount"))
            .order_by("ingredient__name")
        )

        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter="\t")
        writer.writerow(["Список покупок"])
        writer.writerow(["Ингредиенты", "Количество", "Ед. измерения"])

        for item in ingredients:
            writer.writerow(
                [
                    item["ingredient__name"],
                    item["total_amount"],
                    item["ingredient__measurement_unit"],
                ]
            )

        content = buffer.getvalue()
        buffer.close()

        cache.set(cache_key, content, 300)  # кэшируем на 5 минут

        response = HttpResponse(content, content_type="text/csv")
        response["Content-Disposition"] = '''
            attachment; filename="shopping_list.txt"
        '''
        return response

    @action(detail=True, methods=["get"], url_path="get-link")
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        hash_input = f"{recipe.id}{recipe.name}{recipe.created_at}"
        url_hash = self.generate_hash(hash_input)

        short_link, created = RecipeShortLink.objects.get_or_create(
            recipe=recipe, defaults={"url_hash": url_hash}
        )

        short_url = f"{settings.BASE_URL}/a/r/{short_link.url_hash}"
        return Response({"short-link": short_url})

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
        return Response(
            {"error": "Рецепт не найден"},
            status=status.HTTP_404_NOT_FOUND
        )
