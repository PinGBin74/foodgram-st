import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from recipes.models import Recipe, Favorite, ShoppingCart
from ingredient.models import Ingredient

User = get_user_model()


@pytest.fixture
def password():
    return "testpass123"


@pytest.fixture
def user(password):
    return User.objects.create_user(
        username="testuser", email="test@example.com", password=password
    )


@pytest.fixture
def admin_user(password):
    return User.objects.create_superuser(
        username="admin", email="admin@example.com", password=password
    )


@pytest.fixture
def create_users():
    users = []
    for i in range(5):
        user = User.objects.create_user(
            username=f"user{i}", email=f"user{i}@example.com",
            password="testpass123"
        )
        users.append(user)
    return users


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def admin_client(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def user_client_with_token(user):
    client = APIClient()
    token = Token.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


@pytest.fixture
def admin_client_with_token(admin_user):
    client = APIClient()
    token = Token.objects.create(user=admin_user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


@pytest.fixture
def get_token_model():
    return Token


@pytest.fixture
def ingredients():
    ingredients = []
    for i in range(3):
        ingredient = Ingredient.objects.create(
            name=f"Test Ingredient {i}", measurement_unit="g"
        )
        ingredients.append(ingredient)
    return ingredients


@pytest.fixture
def recipes(admin_user, ingredients):
    recipes = []
    for i in range(3):
        recipe = Recipe.objects.create(
            author=admin_user,
            name=f"Test Recipe {i}",
            text=f"Test Description {i}",
            cooking_time=30,
        )
        recipe.ingredients.add(ingredients[0],
                               through_defaults={"amount": 100})
        recipes.append(recipe)
    return recipes


@pytest.fixture
def favorite_recipe(user, recipes):
    Favorite.objects.create(user=user, recipe=recipes[0])
    return recipes[0]


@pytest.fixture
def shopping_recipe(user, recipes):
    ShoppingCart.objects.create(user=user, recipe=recipes[1])
    return recipes[1]
