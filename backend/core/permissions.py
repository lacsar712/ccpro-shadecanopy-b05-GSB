from rest_framework.permissions import IsAuthenticated


class IsAdminRole(IsAuthenticated):
    """仅 role=admin 的用户放行；未登录仍按未认证（401）处理。"""

    message = "仅管理员可执行该操作"

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        user = request.user
        return getattr(user, "role", None) == "admin" or user.is_superuser
