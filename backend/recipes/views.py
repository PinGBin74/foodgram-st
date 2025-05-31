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
from django.db import transaction
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import io
import hashlib
import base64
import logging
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

from const.errors import ERRORS
from const.const import (
    PDF_TITLE,
    PDF_FILENAME,
    PDF_CACHE_TIME,
    PDF_COLUMN_WIDTHS,
    PDF_HEADER_FONT_SIZE,
    PDF_BODY_FONT_SIZE,
    PDF_TITLE_FONT_SIZE,
)


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

    def get_queryset(self):
        """Возвращает отфильтрованный
          список рецептов с оптимизированными запросами."""
        queryset = Recipe.objects.select_related("author").prefetch_related(
            "ingredients"
        )

        if not self.request.user.is_authenticated:
            return queryset

        author = self.request.query_params.get("author")
        is_in_cart = self.request.query_params.get("is_in_shopping_cart")
        is_favorited = self.request.query_params.get("is_favorited")

        if author:
            queryset = queryset.filter(author_id=author)
        if is_in_cart == "1":
            queryset = queryset.filter(shoppingcart__user=self.
                                       request.user).distinct()
        if is_favorited == "1":
            queryset = queryset.filter(favorite__user=self.
                                       request.user).distinct()

        return queryset

    def _invalidate_recipe_caches(self):
        """Invalidate all recipe-related caches."""
        # Clear recipe list caches
        cache.delete("recipes_list_")
        # Clear individual recipe caches
        for recipe in Recipe.objects.values_list("id", flat=True):
            cache.delete(f"recipe_{recipe}")

    @transaction.atomic
    def perform_create(self, serializer):
        """Создает новый рецепт и
        устанавливает текущего пользователя как автора."""
        recipe = serializer.save(author=self.request.user)
        self._invalidate_recipe_caches()
        return recipe

    @transaction.atomic
    def perform_update(self, serializer):
        """Обновляет рецепт, проверяя права доступа автора."""
        if serializer.instance.author != self.request.user:
            raise PermissionDenied(detail=ERRORS["cant_edit"])
        recipe = serializer.save()
        self._invalidate_recipe_caches()
        return recipe

    @transaction.atomic
    def perform_destroy(self, instance):
        """Удаляет рецепт, проверяя права доступа автора."""
        if instance.author != self.request.user:
            raise PermissionDenied(detail=ERRORS["cant_delete"])
        instance.delete()
        self._invalidate_recipe_caches()

    def get_serializer_context(self):
        """Добавляет request в контекст
        сериализатора для доступа к текущему пользователю.
        """
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
        """Добавляет или удаляет рецепт из избранного пользователя."""
        recipe = get_object_or_404(Recipe, id=pk)
        user = request.user

        if request.method == "POST":
            favorite, created = Favorite.objects.get_or_create(
                recipe=recipe, user=user,
                defaults={"recipe": recipe, "user": user}
            )

            if not created:
                return Response(
                    {"error": ERRORS["already_in_favorites"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            serializer = AddFavorite(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == "DELETE":
            deleted, _ = Favorite.objects.filter(
                recipe=recipe, user=user).delete()

            if not deleted:
                return Response(
                    {"errors": ERRORS["not_in_favorites"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(
            {"error": "Method not allowed"},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
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
            cart_item, created = ShoppingCart.objects.get_or_create(
                recipe=recipe,
                user=user,
                defaults={"recipe": recipe, "user": user},
            )

            if not created:
                return Response(
                    {"error": ERRORS["already_in_cart"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            serializer = AddFavorite(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == "DELETE":
            deleted, _ = ShoppingCart.objects.filter(
                recipe=recipe, user=user).delete()

            if not deleted:
                return Response(
                    {"errors": ERRORS["not_in_cart"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(
            {"error": "Method not allowed"},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    @action(
        detail=False,
        methods=("get",),
        permission_classes=[IsAuthenticated],
        url_path="download_shopping_cart",
    )
    def download_shopping_cart(self, request):
        """Скачивает список покупок пользователя в формате PDF."""
        user = request.user
        cache_key = f"shopping_cart_pdf_{user.id}"
        cached_data = cache.get(cache_key)

        if cached_data:
            response = HttpResponse(
                cached_data, content_type="application/pdf"
            )
            response["Content-Disposition"] = (
                f'attachment; filename="{PDF_FILENAME}"'
            )
            return response

        try:
            # Register DejaVuSans font
            font_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "const",
                "fonts",
                "DejaVuSans.ttf",
            )
            pdfmetrics.registerFont(TTFont("DejaVuSans", font_path))

            ingredients = (
                RecipeIngredient.objects.filter(
                    recipe__shoppingcart__user=user)
                .select_related("ingredient")
                .values("ingredient__name", "ingredient__measurement_unit")
                .annotate(total_amount=Sum("amount"))
                .order_by("ingredient__name")
            )

            if not ingredients.exists():
                return Response(
                    {"error": "Shopping cart is empty"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            elements = []

            # Title with Cyrillic support
            title_style = ParagraphStyle(
                "CustomTitle",
                parent=styles["Heading1"],
                fontName="DejaVuSans",
                fontSize=PDF_TITLE_FONT_SIZE,
                spaceAfter=30,
            )
            elements.append(Paragraph(PDF_TITLE, title_style))

            # Table data
            data = [["Ingredient", "Amount", "Unit"]]
            for item in ingredients:
                data.append(
                    [
                        item["ingredient__name"],
                        str(item["total_amount"]),
                        item["ingredient__measurement_unit"],
                    ]
                )

            # Create table
            table = Table(data, colWidths=PDF_COLUMN_WIDTHS)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "DejaVuSans"),
                        ("FONTSIZE", (0, 0), (-1, 0), PDF_HEADER_FONT_SIZE),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                        ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
                        ("FONTNAME", (0, 1), (-1, -1), "DejaVuSans"),
                        ("FONTSIZE", (0, 1), (-1, -1), PDF_BODY_FONT_SIZE),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )

            elements.append(table)
            doc.build(elements)

            pdf_data = buffer.getvalue()
            buffer.close()

            # Cache the PDF data
            cache.set(cache_key, pdf_data, PDF_CACHE_TIME)

            response = HttpResponse(pdf_data, content_type="application/pdf")
            response["Content-Disposition"] = (
                f'attachment; filename="{PDF_FILENAME}"'
            )
            return response

        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}")
            return Response(
                {"error": "Error generating PDF"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["get"], url_path="get-link")
    def get_link(self, request, pk=None):
        """Генерирует короткую ссылку для рецепта."""
        recipe = get_object_or_404(Recipe, id=pk)
        cache_key = f"recipe_short_link_{recipe.id}"
        short_link = cache.get(cache_key)

        if not short_link:
            url_hash = self.generate_hash(str(recipe.id))
            short_link, created = RecipeShortLink.objects.get_or_create(
                recipe=recipe, defaults={"url_hash": url_hash}
            )
            cache.set(cache_key, short_link, 86400)  # Cache for 24 hours

        return Response({
            "short_link": (
                f"{settings.BASE_URL}/api/recipes/short/{short_link.url_hash}"
            )
        })

    def generate_hash(self, input_str):
        """Генерирует короткий хеш для ссылки."""
        hash_object = hashlib.md5(input_str.encode())
        return base64.urlsafe_b64encode(hash_object.digest())[:8].decode()
