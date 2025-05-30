# flake8: noqa: E501
import json
from http import HTTPStatus

import pytest
from rest_framework.reverse import reverse_lazy
from tests.utils import check_pagination, check_recipe_response

from recipes.models import Recipe


@pytest.mark.usefixtures("recipes")
@pytest.mark.django_db
class TestRecipes:
    URL_RECIPIES = reverse_lazy("api:recipe-list")

    @staticmethod
    def get_recipe_detail(recipe_id):
        return reverse_lazy("api:recipe-detail", args=[recipe_id])

    @staticmethod
    def get_short_link(recipe_id):
        return reverse_lazy("api:recipe-get-link", args=[recipe_id])

    @pytest.mark.parametrize(
        "current_client",
        (
            pytest.lazy_fixture("admin_client"),
            pytest.lazy_fixture("user_client"),
            pytest.lazy_fixture("client"),
        ),
    )
    def test_03_get_recipes(self, current_client):
        response = current_client.get(self.URL_RECIPIES)

        assert response.status_code == HTTPStatus.OK

        check_pagination(response.json())

        recipe = response.json()["results"][0]
        check_recipe_response(recipe)

    @pytest.mark.parametrize(
        "current_client, expected_status",
        (
            (
                pytest.lazy_fixture("admin_client_with_token"),
                HTTPStatus.CREATED,
            ),
            (
                pytest.lazy_fixture("user_client_with_token"),
                HTTPStatus.CREATED,
            ),
            (pytest.lazy_fixture("client"), HTTPStatus.UNAUTHORIZED),
        ),
    )
    def test_03_post_recipe(self, current_client, expected_status):
        data = {
            "ingredients": [{"id": 1, "amount": 1}],
            "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABAgMAAABieywaAAAACVBMVEUAAAD///9fX1/S0ecCAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAACklEQVQImWNoAAAAggCByxOyYQAAAABJRU5ErkJggg==",
            "name": "new_ingredient",
            "text": "new_text",
            "cooking_time": 4,
        }
        response = current_client.post(
            self.URL_RECIPIES,
            data=json.dumps(data),
            content_type="application/json",
        )
        assert response.status_code == expected_status, response.json()

        if expected_status != HTTPStatus.CREATED:
            return

        check_recipe_response(response.json())

    def test_03_create_bad_data(self, user_client_with_token):
        bad_data = {
            "ingredients": [{"id": 1, "amount": 1}],
            "image": "",
            "name": "new_ingredient",
            "text": "new_text",
            "cooking_time": 4,
        }
        response = user_client_with_token.post(
            self.URL_RECIPIES,
            data=json.dumps(bad_data),
            content_type="application/json",
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST, response.json()

        bad_data = {
            "ingredients": [{"id": 1, "amount": 1}, {"id": 1, "amount": 5}],
            "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABAgMAAABieywaAAAACVBMVEUAAAD///9fX1/S0ecCAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAACklEQVQImWNoAAAAggCByxOyYQAAAABJRU5ErkJggg==",
            "name": "new_ingredient",
            "text": "new_text",
            "cooking_time": 4,
        }
        response = user_client_with_token.post(
            self.URL_RECIPIES,
            data=json.dumps(bad_data),
            content_type="application/json",
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST, response.json()

        bad_data = {
            "ingredients": [],
            "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABAgMAAABieywaAAAACVBMVEUAAAD///9fX1/S0ecCAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAACklEQVQImWNoAAAAggCByxOyYQAAAABJRU5ErkJggg==",
            "name": "new_ingredient",
            "text": "new_text",
            "cooking_time": 4,
        }
        response = user_client_with_token.post(
            self.URL_RECIPIES,
            data=json.dumps(bad_data),
            content_type="application/json",
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST, response.json()

    @pytest.mark.parametrize(
        "current_client",
        (
            pytest.lazy_fixture("admin_client"),
            pytest.lazy_fixture("user_client"),
            pytest.lazy_fixture("client"),
        ),
    )
    def test_03_get_recipe(self, current_client):
        response = current_client.get(self.get_recipe_detail(1))
        assert response.status_code == HTTPStatus.OK

        check_recipe_response(response.json())

    @pytest.mark.parametrize(
        "current_client, expected_status",
        (
            (pytest.lazy_fixture("admin_client_with_token"), HTTPStatus.OK),
            (
                pytest.lazy_fixture("user_client_with_token"),
                HTTPStatus.FORBIDDEN,
            ),
            (pytest.lazy_fixture("client"), HTTPStatus.UNAUTHORIZED),
        ),
    )
    def test_03_patch_recipe(self, current_client, expected_status):
        data = {
            "ingredients": [{"id": 1, "amount": 1}],
            "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABAgMAAABieywaAAAACVBMVEUAAAD///9fX1/S0ecCAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAACklEQVQImWNoAAAAggCByxOyYQAAAABJRU5ErkJggg==",
            "name": "changed_name",
            "text": "new_text",
            "cooking_time": 4,
        }
        response = current_client.patch(
            self.get_recipe_detail(2),
            data=json.dumps(data),
            content_type="application/json",
        )

        assert response.status_code == expected_status

        recipes_count = Recipe.objects.count() + 1
        response = current_client.patch(
            self.get_recipe_detail(recipes_count),
            data=json.dumps(data),
            content_type="application/json",
        )

        assert (
            response.status_code == HTTPStatus.NOT_FOUND
            if expected_status == HTTPStatus.OK
            else expected_status
        )

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "current_client, expected_status",
        (
            (
                pytest.lazy_fixture("admin_client_with_token"),
                HTTPStatus.NO_CONTENT,
            ),
            (
                pytest.lazy_fixture("user_client_with_token"),
                HTTPStatus.FORBIDDEN,
            ),
            (pytest.lazy_fixture("client"), HTTPStatus.UNAUTHORIZED),
        ),
    )
    def test_03_delete_recipe(self, current_client, expected_status):
        recipes_count = Recipe.objects.count()

        response = current_client.delete(
            self.get_recipe_detail(2),
        )

        assert response.status_code == expected_status
        if expected_status == HTTPStatus.NO_CONTENT:
            recipes_count -= 1
        assert Recipe.objects.count() == recipes_count

    def test_03_link_allowed(self, user_client_with_token):
        response = user_client_with_token.post(self.get_short_link(2))
        assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
