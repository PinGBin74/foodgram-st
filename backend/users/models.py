from django.db import models
from django.contrib.auth.models import AbstractUser
from foodgram.validators import UsernameValidator


class User(AbstractUser):
    first_name = models.CharField(verbose_name="Имя", max_length=150)
    last_name = models.CharField(verbose_name="Фамилия", max_length=150)
    email = models.EmailField(
        verbose_name="Электронная почта",
        max_length=254,
        unique=True,
    )
    username = models.CharField(
        verbose_name="Имя пользователя",
        max_length=150,
        unique=True,
        validators=[UsernameValidator()],
    )
    avatar = models.ImageField(verbose_name="Фото профиля",
                               upload_to="avatar_photos/")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name", "username"]

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return self.username
