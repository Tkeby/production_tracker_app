"""
Simple Django management command to set up reports permissions with Guardian
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from guardian.shortcuts import assign_perm
from reports.models import ReportsPermission

User = get_user_model()


class Command(BaseCommand):
    help = 'Set up basic reports permissions using django-guardian'

    def handle(self, *args, **options):
        self.stdout.write('Setting up reports permissions with Guardian...')
        
        # Create the main reports permission object
        reports_obj, created = ReportsPermission.objects.get_or_create(
            name='Main Reports Dashboard',
            defaults={'description': 'Main reports dashboard access'}
        )
        
        if created:
            self.stdout.write('Created ReportsPermission object')
        else:
            self.stdout.write('ReportsPermission object already exists')
        
        # Assign both view_reports and view_detailed_reports permissions to all superusers
        superusers = User.objects.filter(is_superuser=True)
        for user in superusers:
            assign_perm('reports.view_reports', user, reports_obj)
            assign_perm('reports.view_detailed_reports', user, reports_obj)
            self.stdout.write(f'Assigned view_reports and view_detailed_reports permissions to superuser: {user.email}')
        
        self.stdout.write(
            self.style.SUCCESS('Successfully set up reports permissions!')
        )
        self.stdout.write('')
        self.stdout.write('To assign permissions to other users, use:')
        self.stdout.write('  from guardian.shortcuts import assign_perm')
        self.stdout.write('  from reports.models import ReportsPermission')
        self.stdout.write('  reports_obj = ReportsPermission.objects.get(name="Main Reports Dashboard")')
        self.stdout.write('  assign_perm("reports.view_reports", user, reports_obj)  # Basic reports access')
        self.stdout.write('  assign_perm("reports.view_detailed_reports", user, reports_obj)  # Detailed reports access')
        self.stdout.write('  assign_perm("reports.export_reports", user, reports_obj)  # Export permission')
