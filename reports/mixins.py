"""
Permission mixins for reports views
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from guardian.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from .models import ReportsPermission


class ReportsPermissionMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """
    Mixin that handles object-level permissions for reports using Guardian
    """
    permission_required = 'reports.view_reports'
    raise_exception = True
    
    def get_permission_object(self):
        """
        Return the ReportsPermission object to check permissions against.
        Guardian will check if the user has the required permission on this specific object.
        """
        try:
            return ReportsPermission.objects.get(name='Main Reports Dashboard')
        except ReportsPermission.DoesNotExist:
            # If the permission object doesn't exist, deny access
            raise PermissionDenied("Reports permission object not found. Please run setup_reports command.")
    
    def handle_no_permission(self):
        """
        Custom handler for permission denied cases.
        Renders the 403.html template with context about the user and required permissions.
        """
        if self.raise_exception:
            # Return a 403 response with our custom template
            return render(
                self.request, 
                '403.html', 
                {
                    'required_permission': self.permission_required,
                    'permission_object': 'Reports Dashboard',
                    'user': self.request.user
                }, 
                status=403
            )
        return super().handle_no_permission()


class DetailedReportsPermissionMixin(ReportsPermissionMixin):
    """
    Mixin for views that require detailed reports permission
    """
    permission_required = 'reports.view_detailed_reports'


class ExportReportsPermissionMixin(ReportsPermissionMixin):
    """
    Mixin for views that require export permission
    """
    permission_required = 'reports.export_reports'
