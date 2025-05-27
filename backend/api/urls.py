from django.urls import path, include
from rest_framework import routers

from .views import RecipeViewSet, IngredientViewSet, FollowingViewSet


router = routers.DefaultRouter()
router.register(r"recipes", RecipeViewSet)
router.register(r"ingredients", IngredientViewSet)
router.register(r"users", FollowingViewSet, basename="users")

urlpatterns = [
    path("", include(router.urls)),
    path("", include("djoser.urls")),
    path("auth/", include("djoser.urls.authtoken")),
]
