
from django.urls import path, include
from rest_framework import routers

from recipes.views import RecipeViewSet
from users.views import FollowViewSet

from .views import IngredientViewSet
app_name = 'api'


router = routers.DefaultRouter()
router.register(r"recipes", RecipeViewSet)
router.register(r"ingredients", IngredientViewSet)
router.register(r"users", FollowViewSet, basename="users")

urlpatterns = [
    path("", include(router.urls)),
    path("", include("djoser.urls")),
    path("auth/", include("djoser.urls.authtoken")),
]
