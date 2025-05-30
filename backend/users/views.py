from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import (IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.pagination import LimitOffsetPagination
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet


from api.serializers import FollowSerializer
from users.serializers import UserSerializer
from recipes.serializers import AddAvatar
from const.errors import ERRORS
from recipes.models import (
    User,
    Follow,
)


class FollowViewSet(UserViewSet):
    """ViewSet для работы с подписками пользователей.

    Предоставляет функционал для подписки на авторов, просмотра подписок
    и управления аватаром пользователя.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = LimitOffsetPagination

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[IsAuthenticated],
        url_path="subscribe",
    )
    def subscribe(self, request, id=None):
        """Добавляет или удаляет подписку на автора."""
        user = request.user
        author = get_object_or_404(User, id=id)

        if request.method == "POST":
            if user == author:
                return Response(
                    {"errors": ERRORS["self_subscribe"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if Follow.objects.filter(user=user, author=author).exists():
                return Response(
                    {"errors": ERRORS["already_subscribed"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            Follow.objects.create(user=user, author=author)
            serializer = FollowSerializer(author, context={"request": request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == "DELETE":
            follow = Follow.objects.filter(author=author, user=user)
            if not follow.exists():
                return Response(
                    {"errors": ERRORS["not_subscribed"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            follow.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(
            {"error": "Метод не разрешен"}, status=status.
            HTTP_405_METHOD_NOT_ALLOWED
        )

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated],
        url_path="subscriptions",
    )
    def subscriptions(self, request):
        """Возвращает список авторов, на которых подписан пользователь."""
        user = request.user
        queryset = User.objects.filter(following__user=user).prefetch_related(
            "recipes")
        if not queryset:
            return Response(
                ERRORS["no_subscriptions"], status=status.HTTP_400_BAD_REQUEST
            )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = FollowSerializer(page, many=True, context={"request":
                                                                request})
        return paginator.get_paginated_response(serializer.data)

    @action(detail=False, methods=["get"], permission_classes=[
        IsAuthenticated])
    def me(self, request):
        """Возвращает информацию о текущем пользователе."""
        serializer = UserSerializer(request.user, context={"request": request})
        return Response(serializer.data)

    @action(
        detail=False,
        methods=["get", "put", "patch", "delete"],
        permission_classes=[IsAuthenticated],
        url_path="me/avatar",
    )
    def avatar(self, request):
        """Управляет аватаром пользователя.

        GET - возвращает текущий аватар
        PUT/PATCH - обновляет аватар
        DELETE - удаляет аватар
        """
        user = request.user
        if request.method == "GET":
            serializer = UserSerializer(user, context={"request": request})
            return Response(serializer.data)

        if request.method in ["PUT", "PATCH"]:
            if "avatar" not in request.data:
                return Response(
                    {"errors": ERRORS["no_image"]}, status=status.
                    HTTP_400_BAD_REQUEST
                )
            serializer = AddAvatar(user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        if request.method == "DELETE":
            user.avatar = None
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(
            {"error": "Метод не разрешен"}, status=status.
            HTTP_405_METHOD_NOT_ALLOWED
        )
