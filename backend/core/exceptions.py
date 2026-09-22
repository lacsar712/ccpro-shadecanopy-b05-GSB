from rest_framework import status
from rest_framework.exceptions import APIException


class ZonePausedConflict(APIException):
    """目标分区已暂停时，写入气候/轮灌返回 409。"""

    status_code = status.HTTP_409_CONFLICT
    default_code = "zone_paused"
    default_detail = "该分区已暂停，暂停期间禁止写入"
