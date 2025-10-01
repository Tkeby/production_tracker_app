from django.db.models import Sum, Avg, Count, Q, Case, When, F, Value, FloatField
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
import json
from manufacturing.models import ProductionRun, ProductionReport, ProductionLine, StopEvent, Machine
from .helpers import (
    filter_production_runs, 
    build_production_summary,
    aggregate_basic_totals
)

class ProductionCalculationService:
    """Service class for complex production calculations and analytics"""
    
    @staticmethod
    def calculate_weighted_avg_syrup_yield(queryset) -> Optional[float]:
        """
        Calculate weighted average syrup yield based on production pack proportion
        
        Args:
            queryset: QuerySet of ProductionRun objects
            
        Returns:
            float: Weighted average syrup yield or None if no valid data
        """
        runs_with_data = queryset.select_related('report').filter(
            report__syrup_yield_percentage__isnull=False,
            good_products_pack__gt=0
        )
        
        total_weighted_syrup_yield = Decimal('0')
        total_production_for_yield = 0
        
        for run in runs_with_data:
            if run.report and run.report.syrup_yield_percentage is not None:
                weighted_yield = Decimal(str(run.report.syrup_yield_percentage)) * run.good_products_pack
                total_weighted_syrup_yield += weighted_yield
                total_production_for_yield += run.good_products_pack
        
        if total_production_for_yield > 0:
            return float(total_weighted_syrup_yield / total_production_for_yield)
        return None
    
    @staticmethod
    def calculate_shift_summary(shift_date: date, production_line: Optional[ProductionLine] = None, 
                               shift_type: Optional[str] = None) -> Dict:
        """Calculate summary metrics for a specific shift"""
        
        # Use helper to filter production runs
        queryset = filter_production_runs(shift_date, production_line, shift_type)
        
        # Calculate weighted avg syrup yield based on production pack proportion for each run
        weighted_avg_syrup_yield = ProductionCalculationService.calculate_weighted_avg_syrup_yield(queryset)
        
        # Use helper to build comprehensive production summary
        summary = build_production_summary(queryset, production_line)
        
        # Add weighted average syrup yield to summary
        summary['avg_syrup_yield'] = weighted_avg_syrup_yield
        
        return summary
    
    @staticmethod
    def calculate_daily_summary(target_date: date, production_line: Optional[ProductionLine] = None) -> Dict:
        """Calculate daily production summary across all shifts"""
        
        queryset = ProductionRun.objects.filter(date=target_date)
        
        if production_line:
            queryset = queryset.filter(production_line=production_line)
        
        # Get summary by shifts
        shift_summaries = {}
        for run in queryset:
            shift_key = run.shift.name
            if shift_key not in shift_summaries:
                shift_summaries[shift_key] = {
                    'production_runs': [],
                    'total_production': 0,
                    'total_downtime': 0,
                    'team_leader': run.shift_teamleader.name if hasattr(run.shift_teamleader, 'name') else str(run.shift_teamleader)
                }
            
            shift_summaries[shift_key]['production_runs'].append(run)
            shift_summaries[shift_key]['total_production'] += run.good_products_pack
            shift_summaries[shift_key]['total_downtime'] += run.total_downtime_minutes
        
        # Calculate weighted average syrup yield for daily totals
        weighted_avg_syrup_yield = ProductionCalculationService.calculate_weighted_avg_syrup_yield(queryset)

        # Calculate total production time minutes for daily totals
        total_production_time_minutes_value = 0
        for run in queryset.select_related('shift'):
            total_production_time_minutes_value += run.planned_production_time_minutes

        # Daily totals
        daily_totals = queryset.aggregate(
            total_production=Sum('good_products_pack'),
            total_downtime=Sum('total_downtime_minutes'),
            avg_oee=Avg('report__oee'),
            total_runs=Count('id')
        )
        
        # Add weighted average syrup yield and production time minutes
        daily_totals['avg_syrup_yield'] = weighted_avg_syrup_yield
        daily_totals['total_production_time_minutes'] = total_production_time_minutes_value
        
        return {
            'date': target_date,
            'shifts': shift_summaries,
            'daily_totals': daily_totals,
            'production_line': production_line
        }
    
    @staticmethod
    def calculate_weekly_summary(week_start_date: date, production_line: Optional[ProductionLine] = None) -> Dict:
        """Calculate weekly production summary"""
        
        week_end_date = week_start_date + timedelta(days=6)
        
        queryset = ProductionRun.objects.filter(
            date__range=[week_start_date, week_end_date]
        )
        
        if production_line:
            queryset = queryset.filter(production_line=production_line)
        
        # Daily breakdown
        daily_summaries = {}
        for single_date in (week_start_date + timedelta(n) for n in range(7)):
            daily_summaries[single_date] = ProductionCalculationService.calculate_daily_summary(
                single_date, production_line
            )
        
        # Calculate weighted average syrup yield for weekly totals
        weighted_avg_syrup_yield = ProductionCalculationService.calculate_weighted_avg_syrup_yield(queryset)

        # Calculate total operational minutes by iterating through runs
        # Using the same logic as the planned_production_time_minutes property
        total_production_time_minutes_value = 0
        for run in queryset.select_related('shift'):
            total_production_time_minutes_value += run.planned_production_time_minutes
        
        total_production_time_minutes = total_production_time_minutes_value

        # Weekly totals
        weekly_totals = queryset.aggregate(
            total_production=Sum('good_products_pack'),
            total_downtime=Sum('total_downtime_minutes'),
            avg_oee=Avg('report__oee'),
            total_runs=Count('id')
        )
        
        # Add weighted average syrup yield
        weekly_totals['avg_syrup_yield'] = weighted_avg_syrup_yield
        weekly_totals['total_production_time_minutes'] = total_production_time_minutes
        return {
            'week_start': week_start_date,
            'week_end': week_end_date,
            'daily_summaries': daily_summaries,
            'weekly_totals': weekly_totals,
            'production_line': production_line
        }
    
    @staticmethod
    def get_top_downtime_reasons(start_date: date, end_date: date, 
                                production_line: Optional[ProductionLine] = None, limit: int = 10,
                                machine: Optional[Machine] = None) -> List[Dict]:
        """Get top downtime reasons for a date range"""
        
       
        
        queryset = StopEvent.objects.filter(
            production_run__date__range=[start_date, end_date]
        )
        
        if production_line:
            queryset = queryset.filter(production_run__production_line=production_line)
        if machine:
            queryset = queryset.filter(machine=machine)
        
        downtime_analysis = queryset.values('code__code','code__reason', 'reason', 'machine__machine_name').annotate(
            total_duration=Sum('duration_minutes'),
            occurrence_count=Count('id')
        ).order_by('-total_duration')[:limit]
        
        return list(downtime_analysis)
    
    @staticmethod
    def calculate_oee_trend(start_date: date, end_date: date, 
                          production_line: Optional[ProductionLine] = None,
                          machine: Optional[Machine] = None) -> List[Dict]:
        """Calculate OEE trend over a date range"""
        
        queryset = ProductionReport.objects.filter(
            production_run__date__range=[start_date, end_date]
        )
        
        if production_line:
            queryset = queryset.filter(production_run__production_line=production_line)
        if machine:
            # Filter by production runs that have stop events for this specific machine
            queryset = queryset.filter(production_run__stop_events__machine=machine).distinct()
        
        # Group by date and calculate average OEE
        daily_oee = queryset.values('production_run__date').annotate(
            avg_oee=Avg('oee'),
            avg_availability=Avg('availability'),
            avg_performance=Avg('performance'),
            avg_quality=Avg('quality'),
            runs_count=Count('id')
        ).order_by('production_run__date')
        
        return list(daily_oee)
    
    @staticmethod
    def generate_production_efficiency_report(start_date: date, end_date: date, 
                                            production_line: Optional[ProductionLine] = None,
                                            machine: Optional[Machine] = None) -> Dict:
        """Generate comprehensive production efficiency report"""
        
        # Base metrics
        base_data = {
            'period': {
                'start_date': start_date,
                'end_date': end_date,
                'production_line': production_line.name if production_line else 'All Lines',
                'machine': machine.machine_name if machine else 'All Machines'
            }
        }
        
        # OEE Analysis
        base_data['oee_analysis'] = ProductionCalculationService.calculate_oee_trend(
            start_date, end_date, production_line, machine
        )
        
        # Downtime Analysis
        base_data['downtime_analysis'] = ProductionCalculationService.get_top_downtime_reasons(
            start_date, end_date, production_line, machine=machine
        )
        
        # Production Summary
        queryset = ProductionRun.objects.filter(
            date__range=[start_date, end_date]
        )
        if production_line:
            queryset = queryset.filter(production_line=production_line)
        if machine:
            # Filter production runs that have stop events for this specific machine
            queryset = queryset.filter(stop_events__machine=machine).distinct()
        
        # Calculate weighted average syrup yield for production summary
        weighted_avg_syrup_yield = ProductionCalculationService.calculate_weighted_avg_syrup_yield(queryset)

        production_summary = queryset.aggregate(
            total_production=Sum('good_products_pack'),
            total_downtime=Sum('total_downtime_minutes'),
            avg_oee=Avg('report__oee'),
            total_runs=Count('id')
        )
        
        # Add weighted average syrup yield
        production_summary['avg_syrup_yield'] = weighted_avg_syrup_yield
        base_data['production_summary'] = production_summary
        
        return base_data
    
    @staticmethod
    def get_production_alerts(production_line: Optional[ProductionLine] = None) -> List[Dict]:
        """Get production alerts based on predefined thresholds"""
        
        alerts = []
        today = timezone.now().date()
        
        # Get recent production runs (last 24 hours)
        recent_runs = ProductionRun.objects.filter(
            date=today
        )
        
        if production_line:
            recent_runs = recent_runs.filter(production_line=production_line)
        
        for run in recent_runs:
            if hasattr(run, 'report'):
                report = run.report
                
                # Low OEE Alert
                if report.oee and report.oee < 60:
                    alerts.append({
                        'type': 'LOW_OEE',
                        'severity': 'HIGH' if report.oee < 40 else 'MEDIUM',
                        'message': f"Low OEE ({report.oee}%) in {run.production_batch_number}",
                        'production_run': run,
                        'value': report.oee
                    })
                
                # High Downtime Alert
                if run.total_downtime_minutes > 60:  # More than 1 hour
                    alerts.append({
                        'type': 'HIGH_DOWNTIME',
                        'severity': 'HIGH' if run.total_downtime_minutes > 120 else 'MEDIUM',
                        'message': f"High downtime ({run.total_downtime_minutes} min) in {run.production_batch_number}",
                        'production_run': run,
                        'value': run.total_downtime_minutes
                    })
                
                # Low Quality Alert
                if report.quality and report.quality < 95:
                    alerts.append({
                        'type': 'LOW_QUALITY',
                        'severity': 'HIGH' if report.quality < 90 else 'MEDIUM',
                        'message': f"Low quality ({report.quality}%) in {run.production_batch_number}",
                        'production_run': run,
                        'value': report.quality
                    })
        
        return alerts

    @staticmethod
    def calculate_machine_utilization(start_date: date, end_date: date, 
                                    production_line: ProductionLine) -> Dict:
        """Calculate machine utilization metrics"""
        
        machines = production_line.machine_set.filter(is_active=True)
        utilization_data = {}
        
        for machine in machines:
            # Get production runs for this machine's line
            runs = ProductionRun.objects.filter(
                production_line=production_line,
                date__range=[start_date, end_date]
            )
            
            # Calculate total planned time by iterating through runs and using the property
            total_planned_time = sum([Decimal(str(run.planned_production_time_minutes)) for run in runs])
            total_downtime = runs.aggregate(Sum('total_downtime_minutes'))['total_downtime_minutes__sum'] or 0
            
            if total_planned_time > 0:
                utilization_percentage = ((total_planned_time - total_downtime) / total_planned_time) * 100
            else:
                utilization_percentage = 0
            
            utilization_data[machine.machine_name] = {
                'utilization_percentage': round(utilization_percentage, 2),
                'total_planned_time': total_planned_time,
                'total_downtime': total_downtime,
                'rated_output': machine.rated_output
            }
        
        return utilization_data

    @staticmethod
    def calculate_downtime_pareto(start_date: date, end_date: date, 
                                 production_line: Optional[ProductionLine] = None, limit: int = 10) -> Dict:
        """Calculate Pareto chart data for downtime analysis"""
        
        # Get downtime data
        downtime_data = ProductionCalculationService.get_top_downtime_reasons(
            start_date, end_date, production_line, limit
        )
        
        if not downtime_data:
            return {
                'categories': [],
                'values': [],
                'cumulative_percentages': [],
                'total_duration': 0
            }
        
        # Calculate total duration for percentage calculations
        total_duration = sum(item['total_duration'] for item in downtime_data)
        
        # Prepare Pareto data
        categories = []
        values = []
        cumulative_percentages = []
        cumulative_sum = 0
        
        for item in downtime_data:
            # Create category label
            code_reason = item.get('code__reason', 'Unknown')
            if len(code_reason) > 25:
                code_reason = code_reason[:22] + '...'
            
            categories.append(f"{item['code__code']} - {code_reason}")
            values.append(item['total_duration'])
            
            # Calculate cumulative percentage
            cumulative_sum += item['total_duration']
            cumulative_percentage = (cumulative_sum / total_duration) * 100 if total_duration > 0 else 0
            cumulative_percentages.append(round(cumulative_percentage, 1))
        
        return {
            'categories': categories,
            'values': values,
            'cumulative_percentages': cumulative_percentages,
            'total_duration': total_duration,
            'pareto_80_index': next((i for i, pct in enumerate(cumulative_percentages) if pct >= 80), None)
        }

    @staticmethod
    def calculate_product_trend(start_date: date, end_date: date, 
                              production_line: Optional[ProductionLine] = None) -> Dict:
        """Calculate production trend by product over a date range"""
        
        queryset = ProductionRun.objects.filter(
            date__range=[start_date, end_date]
        )
        
        if production_line:
            queryset = queryset.filter(production_line=production_line)
        
        # Group by product and date to get daily production by product
        product_trend_data = queryset.values(
            'date', 'product__name', 'product__product_code'
        ).annotate(
            total_production=Sum('good_products_pack')
        ).order_by('date', 'product__name')
        
        # Organize data for chart
        products = {}
        dates = set()
        
        for entry in product_trend_data:
            product_name = entry['product__name']
            product_date = entry['date']
            production = entry['total_production'] or 0
            
            dates.add(product_date)
            
            if product_name not in products:
                products[product_name] = {}
            
            products[product_name][product_date] = production
        
        # Sort dates
        sorted_dates = sorted(list(dates))
        
        # Fill missing dates with 0 for each product
        for product_name in products:
            for date_entry in sorted_dates:
                if date_entry not in products[product_name]:
                    products[product_name][date_entry] = 0
        
        # Format data for Chart.js
        chart_data = {
            'labels': [date.strftime('%m/%d') for date in sorted_dates],
            'datasets': []
        }
        
        
        # Define color palette for products
        colors = [
            '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6',
            '#06B6D4', '#84CC16', '#F97316', '#EC4899', '#6366F1'
        ]
        
        for idx, (product_name, product_data) in enumerate(products.items()):
            color = colors[idx % len(colors)]
            dataset = {
                'label': product_name,
                'data': [product_data[date] for date in sorted_dates],
                'borderColor': color,
                'backgroundColor': color + '80',  # More opacity for bars
                'borderWidth': 1,
                'borderRadius': 4,
                'borderSkipped': False,
            }
            chart_data['datasets'].append(dataset)
        
        return {
            'chart_data': chart_data,
            'chart_data_json': json.dumps(chart_data),  # Pre-serialized JSON
            'products': products,
            'date_range': sorted_dates,
            'total_products': len(products)
        }

    @staticmethod
    def calculate_product_summary_by_line_product_package(start_date: date, end_date: date, 
                                                        production_line: Optional[ProductionLine] = None) -> Dict:
        """
        Calculate product summary grouped by Production Line → Product → Package Size
        Returns structured data suitable for creating a product summary table
        """
        
        queryset = ProductionRun.objects.filter(
            date__range=[start_date, end_date]
        )
        
        if production_line:
            queryset = queryset.filter(production_line=production_line)
        
        # Get all unique package sizes to create column headers
        package_sizes = set()
        
        # Get the raw data grouped by line, product, and package size
        raw_data = queryset.values(
            'production_line__name',
            'product__name', 
            'package_size__size',
            'package_size__volume_ml'
        ).annotate(
            total_production=Sum('good_products_pack')
        ).order_by('production_line__name', 'product__name', 'package_size__volume_ml')
        
        # Collect all package sizes for headers
        for entry in raw_data:
            package_sizes.add((entry['package_size__size'], entry['package_size__volume_ml']))
        
        # Sort package sizes by volume for consistent column order
        sorted_package_sizes = sorted(list(package_sizes), key=lambda x: x[1])  # Sort by volume_ml
        
        # Structure the data hierarchically
        summary_data = {}
        line_totals = {}
        package_totals = {size[0]: 0 for size in sorted_package_sizes}
        grand_total = 0
        
        for entry in raw_data:
            line_name = entry['production_line__name']
            product_name = entry['product__name']
            package_size = entry['package_size__size']
            production = entry['total_production'] or 0
            
            # Initialize line if not exists
            if line_name not in summary_data:
                summary_data[line_name] = {}
                line_totals[line_name] = {size[0]: 0 for size in sorted_package_sizes}
                line_totals[line_name]['grand_total'] = 0
            
            # Initialize product if not exists
            if product_name not in summary_data[line_name]:
                summary_data[line_name][product_name] = {size[0]: 0 for size in sorted_package_sizes}
                summary_data[line_name][product_name]['grand_total'] = 0
            
            # Set the production value
            summary_data[line_name][product_name][package_size] = production
            summary_data[line_name][product_name]['grand_total'] += production
            
            # Update line totals
            line_totals[line_name][package_size] += production
            line_totals[line_name]['grand_total'] += production
            
            # Update package totals
            package_totals[package_size] += production
            grand_total += production
        
        return {
            'summary_data': summary_data,
            'line_totals': line_totals,
            'package_sizes': [size[0] for size in sorted_package_sizes],  # Just the size names
            'package_totals': package_totals,
            'grand_total': grand_total,
            'date_range': f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"
        }
