from rest_framework.permissions import BasePermission

from .models import User


class IsAdminRole(BasePermission):
    """仅管理员（role=admin）允许，种植员返回 403。"""

    message = "仅管理员可执行该操作"

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.role == User.ROLE_ADMIN or user.is_superuser)
        )
