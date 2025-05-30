import base64
import binascii
from django.core.files.base import ContentFile
from rest_framework import serializers

from const.errors import ERROR_MESSAGES

ALLOWED_IMAGE_FORMATS = ["jpeg", "jpg", "png", "gif"]


class ImageField(serializers.ImageField):
    """Поле для кодирования/декодирования изображения Base64"""

    def to_internal_value(self, data):
        try:
            if isinstance(data, str) and data.startswith("data:image"):
                parts = data.split(";base64,")
                if len(parts) != 2:
                    raise serializers.ValidationError(
                        ERROR_MESSAGES["invalid_base64"])

                format_part = parts[0]
                imgstr = parts[1]

                ext = format_part.split("/")[-1]
                if ext not in ALLOWED_IMAGE_FORMATS:
                    raise serializers.ValidationError(
                        ERROR_MESSAGES["invalid_image_format"]
                    )

                try:
                    decoded_file = base64.b64decode(imgstr)
                except (TypeError, binascii.Error):
                    raise serializers.ValidationError(
                        ERROR_MESSAGES["invalid_base64_data"]
                    )

                data = ContentFile(decoded_file, name=f"photo.{ext}")

            return super().to_internal_value(data)

        except Exception as e:
            raise serializers.ValidationError(str(e))
