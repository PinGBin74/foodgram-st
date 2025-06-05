from django.urls import include, path
from rest_framework.routers import DefaultRouter

from ingredient.views import IngredientViewSet
from recipe.views import RecipeViewSet
from users.views import UserViewSet

router = DefaultRouter()
router.register(r"ingredients", IngredientViewSet, basename="ingredients")
router.register(r"recipes", RecipeViewSet, basename="recipes")
router.register(r"users", UserViewSet, basename="users")

urlpatterns = [
    path("", include(router.urls)),
    path("auth/", include("djoser.urls")),
    path("auth/", include("djoser.urls.authtoken")),
]
