"""
Admin configuration for reports app
"""
from django.contrib import admin
from guardian.admin import GuardedModelAdmin
from .models import ReportsPermission


@admin.register(ReportsPermission)
class ReportsPermissionAdmin(GuardedModelAdmin):
    """Admin for ReportsPermission with Guardian integration"""
    list_display = ['name', 'description']
    search_fields = ['name', 'description']