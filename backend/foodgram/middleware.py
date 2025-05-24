import json
import logging

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Логируем входящий запрос
        try:
            body = json.loads(request.body.decode("utf-8"))
        except:
            body = request.body.decode("utf-8", errors="replace")

        logger.debug(
            f"Request: {request.method} {request.path}\n"
            f"Headers: {dict(request.headers)}\n"
            f"Body: {body}"
        )

        response = self.get_response(request)

        # Логируем ответ
        logger.debug(
            f"Response: {response.status_code}\n"
            f"Headers: {dict(response.headers)}\n"
            f"Content: {response.content.decode('utf-8', errors='replace')}"
        )

        return response
