import re
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible


@deconstructible
class UsernameValidator:
    def __init__(self, pattern=r"^[\w.@+-]+$"):
        self.pattern = pattern
        self.regex = re.compile(pattern)

    def __call__(self, value):
        if not self.regex.fullmatch(value):
            raise ValidationError(
                "Username может содержать только латинские буквы, "
                "цифры и знаки @/./+/-/_"
            )

    def get_help_text(self):
        return (
            "Username может содержать только латинские буквы, "
            "цифры и знаки @/./+/-/_"
        )
