from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from djoser.views import UserViewSet
import logging
from django.contrib.auth import get_user_model
from reportlab.pdfgen import canvas
from io import BytesIO

from .serializers import (
    RecipeSerializer,
    IngredientSerializer,
    CustomUserSerializer,
    TagSerializer,
    RecipeCreateSerializer,
)
from recipes.models import (
    Recipe,
    Ingredient,
    Favorite,
    ShoppingCart,
    RecipeIngredient,
    Tag,
    Subscription,
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
            if Subscription.objects.filter(user=user, author=author).exists():
                return Response(
                    {"error": "You are already subscribed to this user."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            Subscription.objects.create(user=user, author=author)
            serializer = self.get_serializer(author)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == "DELETE":
            if not Subscription.objects.filter(user=user, author=author).exists():
                return Response(
                    {"error": "You are not subscribed to this user."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            Subscription.objects.filter(user=user, author=author).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        user = request.user
        queryset = User.objects.filter(subscribers__user=user)
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
            if model.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {"error": f"Recipe is already in {related_name}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            model.objects.create(user=user, recipe=recipe)
            serializer = RecipeSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == "DELETE":
            if not model.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {"error": f"Recipe is not in {related_name}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            model.objects.filter(user=user, recipe=recipe).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        user = request.user
        ingredients = (
            RecipeIngredient.objects.filter(recipe__shopping_cart__user=user)
            .values("ingredient__name", "ingredient__measurement_unit")
            .annotate(amount=Sum("amount"))
        )

        format_type = request.query_params.get("format", "txt")

        if format_type == "pdf":
            buffer = BytesIO()
            p = canvas.Canvas(buffer)
            p.drawString(100, 800, "Shopping List:")
            y = 750

            for ingredient in ingredients:
                text = (
                    f'{ingredient["ingredient__name"]} - '
                    f'{ingredient["amount"]} '
                    f'{ingredient["ingredient__measurement_unit"]}'
                )
                p.drawString(100, y, text)
                y -= 20

            p.showPage()
            p.save()
            buffer.seek(0)

            response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
            response["Content-Disposition"] = 'attachment; filename="shopping_list.pdf"'
            return response

        # Default to txt format
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
