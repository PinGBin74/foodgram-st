from http import HTTPStatus


def check_pagination(json_response):
    for field in ("count", "next", "previous", "results"):
        assert field in json_response, (
            f"Response does not contain field {field!r}"
        )


def check_recipe_response(result):
    fields = (
        "id",
        "author",
        "ingredients",
        "is_favorited",
        "is_in_shopping_cart",
        "name",
        "image",
        "text",
        "cooking_time",
    )
    for field in fields:
        assert field in result, f"Missing field {field}"

    result_author = result["author"]
    assert isinstance(result_author, dict), "Author should be a dict"
    fields = (
        "email",
        "id",
        "username",
        "first_name",
        "last_name",
        "is_subscribed",
        "avatar",
    )
    for field in fields:
        assert field in result_author, (
            f"Missing field {field}"
        )
    assert isinstance(result["ingredients"], list), (
        "Ingredients should be a list"
    )

    # Проверяем поля ингредиентов только если список не пустой
    if result["ingredients"]:
        result_ingredients = result["ingredients"][0]
        fields = ("id", "name", "measurement_unit", "amount")
        for field in fields:
            assert field in result_ingredients, (
                f"Missing field {field}"
            )


def check_author_recipe(current_client, expected_status, url_func):
    url = url_func(1)
    last_recipe_id = 664721
    response = current_client.post(url_func(last_recipe_id + 1))
    assert response.status_code in (
        HTTPStatus.BAD_REQUEST,
        HTTPStatus.UNAUTHORIZED,
    ), response.json()

    response = current_client.post(url)
    assert response.status_code == expected_status

    if expected_status == HTTPStatus.CREATED:
        bad_response = current_client.post(url)
        assert bad_response.status_code == HTTPStatus.BAD_REQUEST

        fields = ("id", "name", "image", "cooking_time")
        json_response = response.json()
        assert len(json_response) == len(fields), (
            f"Expected {len(fields)} fields, got {len(json_response)}"
        )

        for field in fields:
            assert field in json_response, (
                f"Field {field} not found in response"
            )

    response = current_client.delete(url, content_type="application/json")
    assert response.status_code in (
        HTTPStatus.NO_CONTENT,
        HTTPStatus.UNAUTHORIZED,
    ), response
    response = current_client.delete(url, content_type="application/json")
    assert response.status_code in (
        HTTPStatus.BAD_REQUEST,
        HTTPStatus.UNAUTHORIZED,
    ), response
