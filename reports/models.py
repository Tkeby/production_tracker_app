"""
Reports app models for permissions
"""
from django.db import models


class ReportsPermission(models.Model):
    """
    A simple model to hold permissions for the reports app.
    This allows us to use Guardian's object-level permissions.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    class Meta:
        permissions = (
            ('view_reports', 'Can view reports dashboard'),
            ('view_detailed_reports', 'Can view detailed reports'),
            ('export_reports', 'Can export reports'),
        )
    
    def __str__(self):
        return self.name