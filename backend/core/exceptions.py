from rest_framework.exceptions import APIException


class ZonePausedConflict(APIException):
    """分区已暂停时仍试图新建气候/轮灌（或把记录转入暂停区），返回 409。

    响应体扁平返回分区编号、编码与是否暂停，detail 为中文说明。
    """

    status_code = 409
    default_code = "zone_paused"

    def __init__(self, zone, action_label):
        self.payload = {
            "detail": f"分区「{zone.zone_code}」已暂停，{action_label}",
            "zoneId": zone.id,
            "zoneCode": zone.zone_code,
            "isPaused": True,
        }
        super().__init__(self.payload["detail"])
