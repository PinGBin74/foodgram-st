from django.contrib.auth.models import AbstractUser
from django.db import models

from foodgram.validators import validate_username


class User(AbstractUser):
    email = models.EmailField(
        verbose_name="Email",
        max_length=254,
        unique=True,
    )
    username = models.CharField(
        verbose_name="Логин",
        max_length=150,
        unique=True,
        validators=[validate_username],
    )
    first_name = models.CharField(
        verbose_name="Имя",
        max_length=150,
    )
    last_name = models.CharField(
        verbose_name="Фамилия",
        max_length=150,
    )
    password = models.CharField(
        verbose_name="Пароль",
        max_length=150,
    )
    avatar = models.ImageField(verbose_name="Фото профиля", upload_to="avatar_photos/")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name", "username"]

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ["id"]

    def __str__(self):
        return self.username
