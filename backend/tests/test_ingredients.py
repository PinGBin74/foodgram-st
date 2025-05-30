# flake8: noqa: E501
from http import HTTPStatus

import pytest
from rest_framework.reverse import reverse_lazy


INGREDIENTS_FIELDS = ("id", "name", "measurement_unit")


@pytest.mark.django_db
@pytest.mark.usefixtures("ingredients")
class TestIngredient:
    URL_INGREDIENTS = reverse_lazy("api:ingredient-list")
    URL_INGREDIENTS_DETAILS = reverse_lazy("api:ingredient-detail", args=[1])

    @pytest.mark.parametrize(
        "current_client",
        (pytest.lazy_fixture("admin_client"), pytest.lazy_fixture("client")),
    )
    def test_07_get_ingredients(self, current_client):
        response = current_client.get(self.URL_INGREDIENTS)
        assert response.status_code == HTTPStatus.OK

        assert isinstance(response.json(), list), "Response should be a list"

        json_response = response.json()[0]
        assert len(json_response) == len(
            INGREDIENTS_FIELDS
        ), f"Response should be {len(INGREDIENTS_FIELDS)}. Got {len(json_response)}"
        for field in INGREDIENTS_FIELDS:
            assert field in json_response, f"Field {field} should be in the response"

    @pytest.mark.parametrize(
        "current_client",
        (pytest.lazy_fixture("admin_client"), pytest.lazy_fixture("client")),
    )
    def test_07_get_ingredients_detail(self, current_client):
        response = current_client.get(self.URL_INGREDIENTS_DETAILS)

        assert response.status_code == HTTPStatus.OK

        json_response = response.json()

        assert len(json_response) == len(
            INGREDIENTS_FIELDS
        ), f"Response should be {len(INGREDIENTS_FIELDS)}. Got {len(json_response)}"
        for field in INGREDIENTS_FIELDS:
            assert field in json_response, f"Field {field} should be in the response"

    def test_07_search_ingredients(self, client):
        response = client.get(self.URL_INGREDIENTS + "?name=A")
        assert response.status_code == HTTPStatus.OK
        json_response = response.json()
        assert all(
            map(lambda i: i["name"].startswith("A"), json_response)
        ), 'All ingredients should start with "A"'

    def test_07_get_bad_ingredients(self, client):
        ingredient_id = 66464642
        response = client.get(
            reverse_lazy("api:ingredient-detail", args=[ingredient_id])
        )

        assert response.status_code == HTTPStatus.NOT_FOUND
