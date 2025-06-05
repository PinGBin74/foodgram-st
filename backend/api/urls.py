from django.urls import include, path
from rest_framework.routers import DefaultRouter

from ingredient.views import IngredientViewSet
from recipe.views import RecipeViewSet
from users.views import UserViewSet

router = DefaultRouter()
router.register(r'ingredients', IngredientViewSet)
router.register(r'recipes', RecipeViewSet)
router.register(r'users', UserViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
]