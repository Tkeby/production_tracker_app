from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from manufacturing.models import ProductionRun
from manufacturing.services import ProductionCalculationService


class Command(BaseCommand):
    help = 'Calculate and update production reports for specified date range'

    def add_arguments(self, parser):
        parser.add_argument(
            '--start-date',
            type=str,
            help='Start date in YYYY-MM-DD format (default: yesterday)',
        )
        parser.add_argument(
            '--end-date', 
            type=str,
            help='End date in YYYY-MM-DD format (default: yesterday)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recalculation even if reports already exist',
        )

    def handle(self, *args, **options):
        # Parse dates
        if options['start_date']:
            start_date = date.fromisoformat(options['start_date'])
        else:
            start_date = timezone.now().date() - timedelta(days=1)
            
        if options['end_date']:
            end_date = date.fromisoformat(options['end_date'])
        else:
            end_date = start_date

        self.stdout.write(f"Calculating reports from {start_date} to {end_date}")

        # Get production runs in date range
        production_runs = ProductionRun.objects.filter(
            date__range=[start_date, end_date],
            is_completed=True
        )

        if not options['force']:
            # Only process runs without reports
            production_runs = production_runs.filter(report__isnull=True)

        processed_count = 0
        for run in production_runs:
            try:
                report = run.update_calculations()
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Calculated report for {run.production_batch_number}")
                )
                processed_count += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"✗ Error calculating report for {run.production_batch_number}: {e}")
                )

        self.stdout.write(
            self.style.SUCCESS(f"Successfully processed {processed_count} production runs")
        )