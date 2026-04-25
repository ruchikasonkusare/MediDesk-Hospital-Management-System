from rest_framework.permissions import BasePermission, SAFE_METHODS


def get_role(user):
    if user.is_superuser:
        return 'admin'
    try:
        return user.profile.role
    except Exception:
        return 'receptionist'


class IsAdminRole(BasePermission):
    """Only admin users."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and get_role(request.user) == 'admin'


class IsAdminOrReceptionist(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and get_role(request.user) in ('admin', 'receptionist')


class IsAdminOrDoctor(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and get_role(request.user) in ('admin', 'doctor')


class IsDoctor(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and get_role(request.user) == 'doctor'


class IsPharmacist(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and get_role(request.user) == 'pharmacist'


class ReadOnlyOrAdmin(BasePermission):
    """Safe methods for all authenticated; write only for admin."""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return get_role(request.user) == 'admin'


class MediDeskAPIPermission(BasePermission):
    """
    Flexible permission — checks role against a per-view allowed_roles attribute.
    Views can set: allowed_roles = ['admin', 'doctor']
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        allowed = getattr(view, 'allowed_roles', None)
        if allowed is None:
            return True
        return get_role(request.user) in allowed
