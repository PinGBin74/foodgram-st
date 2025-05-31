import base64
import binascii
import logging
from django.core.files.base import ContentFile
from rest_framework import serializers

from const.errors import ERROR_MESSAGES

ALLOWED_IMAGE_FORMATS = ["jpeg", "jpg", "png", "gif"]
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

logger = logging.getLogger(__name__)


class ImageField(serializers.ImageField):
    """Поле для кодирования/декодирования изображения Base64.

    Поддерживает загрузку изображений в форматах: jpeg, jpg, png, gif.
    Максимальный размер файла: 5MB.
    """

    def to_internal_value(self, data):
        try:
            if not isinstance(data, str):
                return super().to_internal_value(data)

            if not data.startswith("data:image"):
                logger.warning(
                    "Invalid image data format: "
                    "missing data:image prefix"
                )
                raise serializers.ValidationError(
                    ERROR_MESSAGES["invalid_base64"]
                )

            try:
                format_part, imgstr = data.split(";base64,", 1)
            except ValueError:
                logger.warning("Invalid base64 format: missing separator")
                raise serializers.ValidationError(
                    ERROR_MESSAGES["invalid_base64"]
                )

            try:
                ext = format_part.split("/")[-1].lower()
            except (IndexError, AttributeError):
                logger.warning("Invalid image format specification")
                raise serializers.ValidationError(
                    ERROR_MESSAGES["invalid_image_format"]
                )

            if ext not in ALLOWED_IMAGE_FORMATS:
                logger.warning(f"Unsupported image format: {ext}")
                raise serializers.ValidationError(
                    ERROR_MESSAGES["invalid_image_format"]
                )

            try:
                decoded_file = base64.b64decode(imgstr)
            except (TypeError, binascii.Error) as e:
                logger.error(f"Base64 decoding error: {str(e)}")
                raise serializers.ValidationError(
                    ERROR_MESSAGES["invalid_base64_data"]
                )

            if len(decoded_file) > MAX_IMAGE_SIZE:
                logger.warning(
                    f"Image size exceeds limit: "
                    f"{len(decoded_file)} bytes"
                )
                raise serializers.ValidationError(
                    ERROR_MESSAGES.get(
                        "image_too_large",
                        "Image size exceeds limit"
                    )
                )

            data = ContentFile(decoded_file, name=f"photo.{ext}")
            return super().to_internal_value(data)

        except serializers.ValidationError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in ImageField: {str(e)}")
            raise serializers.ValidationError(
                ERROR_MESSAGES.get("image_processing_error", str(e))
            )
