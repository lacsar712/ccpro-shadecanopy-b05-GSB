from rest_framework.views import exception_handler as drf_exception_handler


def custom_exception_handler(exc, context):
    """在 DRF 默认处理基础上，保留带结构化 payload 的业务异常（如暂停冲突 409）。"""
    response = drf_exception_handler(exc, context)
    payload = getattr(exc, "payload", None)
    if response is not None and payload is not None:
        response.data = payload
    return response
