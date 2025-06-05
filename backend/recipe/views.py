from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from django.db.models import Sum

from .models import Recipe, Favorite, ShoppingCart, RecipeIngredient
from .serializers import RecipeSerializer
from .short_serializers import ShortRecipeSerializer
from .filters import RecipeFilter


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

    def get_filterset(self, *args, **kwargs):
        filterset = super().get_filterset(*args, **kwargs)
        filterset.request = self.request
        return filterset

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        if self.get_object().author != self.request.user:
            return Response(
                {"detail": "Недостаточно прав"}, status=status.HTTP_403_FORBIDDEN
            )
        serializer.save()

    def perform_destroy(self, instance):
        if instance.author != self.request.user:
            return Response(
                {"detail": "Недостаточно прав"}, status=status.HTTP_403_FORBIDDEN
            )
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated],
        url_path="favorite",
    )
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)
        if Favorite.objects.filter(user=request.user, recipe=recipe).exists():
            return Response(
                {"errors": "Рецепт уже в избранном"}, status=status.HTTP_400_BAD_REQUEST
            )
        Favorite.objects.create(user=request.user, recipe=recipe)
        serializer = ShortRecipeSerializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["delete"],
        permission_classes=[IsAuthenticated],
        url_path="favorite",
    )
    def favorite_delete(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)
        favorite = Favorite.objects.filter(user=request.user, recipe=recipe)
        if not favorite.exists():
            return Response(
                {"errors": "Рецепта нет в избранном"},
                status=status.HTTP_404_NOT_FOUND,
            )
        favorite.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated],
        url_path="shopping_cart",
    )
    def shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)
        if ShoppingCart.objects.filter(user=request.user, recipe=recipe).exists():
            return Response(
                {"errors": "Рецепт уже в списке покупок"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ShoppingCart.objects.create(user=request.user, recipe=recipe)
        serializer = ShortRecipeSerializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["delete"],
        permission_classes=[IsAuthenticated],
        url_path="shopping_cart",
    )
    def shopping_cart_delete(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)
        cart = ShoppingCart.objects.filter(user=request.user, recipe=recipe)
        if not cart.exists():
            return Response(
                {"errors": "Рецепта нет в списке покупок"},
                status=status.HTTP_404_NOT_FOUND,
            )
        cart.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"])
    def get_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)
        short_link = f"https://foodgram.example.org/s/{recipe.id}"
        return Response({"short-link": short_link}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        ingredients = (
            RecipeIngredient.objects.filter(recipe__in_shopping_cart__user=request.user)
            .values("ingredient__name", "ingredient__measurement_unit")
            .annotate(total_amount=Sum("amount"))
        )

        content = "\n".join(
            [
                f"{item['ingredient__name']} "
                f"({item['ingredient__measurement_unit']}) — "
                f"{item['total_amount']}"
                for item in ingredients
            ]
        )
        response = HttpResponse(content, content_type="text/plain")
        response["Content-Disposition"] = 'attachment; filename="shopping_list.txt"'
        return response
