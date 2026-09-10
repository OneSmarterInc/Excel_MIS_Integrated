from rest_framework.permissions import BasePermission


class IsFaculty(BasePermission):
    message = "Only a faculty account can do this."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_faculty)


class IsStudent(BasePermission):
    message = "Only a student account can do this."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_student)


class IsAdminRole(BasePermission):
    message = "Only an admin account can do this."

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.is_admin_user
        )
