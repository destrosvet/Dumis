from rest_framework.permissions import BasePermission
from django.utils.translation import gettext_lazy as _


class HasPermission(BasePermission):
    """Wraps user.has_perm(<codename>) for views that declare `required_permission`."""

    message = _("You do not have permission to perform this action.")

    def has_permission(self, request, view):
        required = getattr(view, 'required_permission', None)
        if required is None:
            return True
        return bool(request.user and request.user.has_perm(required))
