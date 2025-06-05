from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets

from .models import Ingredient
from .serializers import IngredientSerializer


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ("name",)
    search_fields = ("^name",)
