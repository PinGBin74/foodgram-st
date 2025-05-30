# flake8: noqa: E501
from http import HTTPStatus

import pytest
from rest_framework.reverse import reverse_lazy

from .utils import check_pagination


SHORT_USER_FIELDS = ("email", "id", "username", "first_name", "last_name")
USER_FIELDS = (
    "email",
    "id",
    "username",
    "first_name",
    "last_name",
    "is_subscribed",
    "avatar",
)


class Test01Users:
    URL_USERS = reverse_lazy("api:users-list")
    URL_ME = reverse_lazy("api:users-me")
    URL_ME_AVATAR = reverse_lazy("api:users-avatar")
    URL_CHANGE_PASSWORD = URL_USERS + "set_password/"

    URL_GET_TOKEN = reverse_lazy("api:login")
    URL_DELETE_TOKEN = reverse_lazy("api:logout")

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "current_client",
        (
            pytest.lazy_fixture("admin_client"),
            pytest.lazy_fixture("user_client"),
            pytest.lazy_fixture("client"),
        ),
    )
    @pytest.mark.usefixtures("admin_user")
    def test_01_get_users(self, current_client):
        response = current_client.get(self.URL_USERS)
        assert response.status_code == HTTPStatus.OK

        json_response = response.json()
        check_pagination(json_response)

        results = json_response["results"][0]

        for field in USER_FIELDS:
            assert field in results, f"Response does not contain field {field!r}"

        assert len(results) == len(
            USER_FIELDS
        ), f"Response contains {len(results)}, expected {len(USER_FIELDS)}"

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "current_client",
        (
            pytest.lazy_fixture("admin_client"),
            pytest.lazy_fixture("user_client"),
            pytest.lazy_fixture("client"),
        ),
    )
    def test_01_get_current_user(self, current_client, admin_user):
        response = current_client.get(self.URL_USERS + f"{admin_user.id}/")
        assert response.status_code == HTTPStatus.OK

        json_response = response.json()
        for field in USER_FIELDS:
            assert field in json_response, f"Response does not contain field {field}"

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "current_client, expected_status, bad_status",
        (
            (
                pytest.lazy_fixture("admin_client_with_token"),
                HTTPStatus.OK,
                HTTPStatus.BAD_REQUEST,
            ),
            (
                pytest.lazy_fixture("user_client_with_token"),
                HTTPStatus.OK,
                HTTPStatus.BAD_REQUEST,
            ),
            (
                pytest.lazy_fixture("client"),
                HTTPStatus.UNAUTHORIZED,
                HTTPStatus.UNAUTHORIZED,
            ),
        ),
    )
    def test_01_put_me_avatar(self, current_client, expected_status, bad_status):
        bad_data = {}
        response = current_client.put(self.URL_ME_AVATAR, data=bad_data)
        assert response.status_code == bad_status, response.json()

        data = {
            "avatar": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABAgMAAABieywaAAAACVBMVEUAAAD///9fX1/S0ecCAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAACklEQVQImWNoAAAAggCByxOyYQAAAABJRU5ErkJggg=="
        }

        response = current_client.put(self.URL_ME_AVATAR, data=data)
        assert response.status_code == expected_status

        if expected_status != HTTPStatus.OK:
            return

        json_response = response.json()
        fields = ("avatar",)

        for field in fields:
            assert field in json_response, f"Response does not contain field {field}"

        assert len(json_response) == len(
            fields
        ), f"Response contains {len(json_response)}, expected {len(fields)}"

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
                HTTPStatus.NO_CONTENT,
            ),
            (pytest.lazy_fixture("client"), HTTPStatus.UNAUTHORIZED),
        ),
    )
    def test_01_delete_me_avatar(self, current_client, expected_status):
        response = current_client.delete(self.URL_ME_AVATAR)

        assert response.status_code == expected_status, response.json()

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "current_client, current_user, expected_status",
        (
            (
                pytest.lazy_fixture("admin_client_with_token"),
                pytest.lazy_fixture("admin_user"),
                HTTPStatus.NO_CONTENT,
            ),
            (
                pytest.lazy_fixture("client"),
                pytest.lazy_fixture("user"),
                HTTPStatus.UNAUTHORIZED,
            ),
        ),
    )
    def test_01_change_password(
        self, current_client, current_user, expected_status, password
    ):
        data = {
            "new_password": "new_password",
            "current_password": password,
        }
        response = current_client.post(self.URL_CHANGE_PASSWORD, data=data)

        assert response.status_code == expected_status

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "current_user, current_client",
        (
            (
                pytest.lazy_fixture("admin_user"),
                pytest.lazy_fixture("admin_client"),
            ),
            (
                pytest.lazy_fixture("user"),
                pytest.lazy_fixture("user_client"),
            ),
        ),
    )
    def test_01_get_token(self, current_client, current_user, password):
        data = {"password": password, "email": current_user.email}

        response = current_client.post(self.URL_GET_TOKEN, data=data)

        assert response.status_code == HTTPStatus.OK  # HTTPStatus.CREATED

        assert "auth_token" in response.json(), "Auth token is missing"
