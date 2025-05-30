import pytest
from django.urls import reverse_lazy


@pytest.mark.django_db
@pytest.mark.usefixtures("recipes")
class TestSubscribers:
    URL_SUBSCRIBERS = reverse_lazy("api:users-subscriptions")

    @staticmethod
    def url_subscribe_detail(pk):
        return reverse_lazy("api:users-subscribe", args=[pk])

    def test_02_subscribe_with_query(self, user_client_with_token, admin_user):
        recipes_limit = 1
        url = self.url_subscribe_detail(admin_user.id)
        response = user_client_with_token.post(
            f"{url}?recipes_limit={recipes_limit}"
        )
        json_response = response.json()["recipes"]
        assert (
            len(json_response) == recipes_limit
        ), f"Expected {recipes_limit} response, got {len(json_response)}"
