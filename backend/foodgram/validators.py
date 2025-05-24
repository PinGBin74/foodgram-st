import re
from django.core.exceptions import ValidationError


class AllowedCharactersPasswordValidator:
    def __init__(self, pattern):
        self.pattern = pattern
        self.regex = re.compile(pattern)

    def validate(self, password, user=None):
        if not self.regex.fullmatch(password):
            raise ValidationError(
                f"Пароль содержит недопустимые символы. Разрешены только: {self.pattern}"
            )

    def get_help_text(self):
        return f"Пароль должен содержать только символы, соответствующие шаблону: {self.pattern}"
