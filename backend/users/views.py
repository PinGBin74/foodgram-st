from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from djoser.views import UserViewSet as DjoserUserViewSet

from .models import User, Follow
from .serializers import (
    CustomUserSerializer,
    UserCreateSerializer,
    SubscriptionSerializer,
    AvatarSerializer,
    SetPasswordSerializer,
)


class UserViewSet(DjoserUserViewSet):
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ["subscribe", "subscriptions"]:
            return SubscriptionSerializer
        if self.action in ["avatar", "avatar_delete"]:
            return AvatarSerializer
        if self.action == "set_password":
            return SetPasswordSerializer
        return super().get_serializer_class()

    @action(
        detail=True, methods=["POST", "DELETE"], permission_classes=[IsAuthenticated]
    )
    def subscribe(self, request, id=None):
        user = request.user
        following = get_object_or_404(User, id=id)
        if user == following:
            return Response(
                {"errors": "Нельзя подписаться на себя"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if request.method == "POST":
            if Follow.objects.filter(user=user, following=following).exists():
                return Response(
                    {"errors": "Вы уже подписаны"}, status=status.HTTP_400_BAD_REQUEST
                )
            Follow.objects.create(user=user, following=following)
            serializer = self.get_serializer(following, context={"request": request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:  # DELETE
            follow = Follow.objects.filter(user=user, following=following)
            if not follow.exists():
                return Response(
                    {"errors": "Вы не подписаны на этого пользователя"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            follow.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["GET"], permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        queryset = User.objects.filter(following__user=request.user)
        page = self.paginate_queryset(queryset)
        serializer = SubscriptionSerializer(
            page, many=True, context={"request": request}
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=False,
        methods=["PUT"],
        permission_classes=[IsAuthenticated],
        url_path="me/avatar",
    )
    def avatar(self, request):
        serializer = AvatarSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=False,
        methods=["DELETE"],
        permission_classes=[IsAuthenticated],
        url_path="me/avatar",
    )
    def avatar_delete(self, request):
        user = request.user
        if not user.avatar:
            return Response(
                {"errors": "Аватар не установлен"}, status=status.HTTP_400_BAD_REQUEST
            )
        user.avatar.delete(save=True)
        user.avatar = None
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=["POST"],
        permission_classes=[IsAuthenticated],
        url_path="set_password",
    )
    def set_password(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not request.user.check_password(
            serializer.validated_data["current_password"]
        ):
            return Response(
                {"current_password": ["Неверный текущий пароль"]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
