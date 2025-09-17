from django.db.models import Sum, Avg, Count, Q
from django.utils import timezone
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
from manufacturing.models import ProductionRun, ProductionReport, ProductionLine,StopEvent

class ProductionCalculationService:
    """Service class for complex production calculations and analytics"""
    
    @staticmethod
    def calculate_shift_summary(shift_date: date, production_line: Optional[ProductionLine] = None, 
                               shift_type: Optional[str] = None) -> Dict:
        """Calculate summary metrics for a specific shift"""
        
        queryset = ProductionRun.objects.filter(date=shift_date)
        
        if production_line:
            queryset = queryset.filter(production_line=production_line)
        
        if shift_type:
            queryset = queryset.filter(shift__name=shift_type)
        
        # Aggregate data
        summary = queryset.aggregate(
            total_production=Sum('good_products_pack'),
            total_downtime=Sum('total_downtime_minutes'),
            avg_oee=Avg('report__oee'),
            production_runs_count=Count('id'),
            total_syrup=Sum('final_syrup_volume')
        )
        
        # Calculate additional metrics
        total_planned_time = sum([run.planned_production_time_minutes for run in queryset])
        summary.update({
            'total_planned_time_minutes': total_planned_time,
            'availability_percentage': ((total_planned_time - (summary['total_downtime'] or 0)) / 
                                      total_planned_time * 100) if total_planned_time > 0 else 0,
            'runs': queryset.select_related('product', 'package_size', 'shift_teamleader')
        })
        
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
        
        # Daily totals
        daily_totals = queryset.aggregate(
            total_production=Sum('good_products_pack'),
            total_downtime=Sum('total_downtime_minutes'),
            avg_oee=Avg('report__oee'),
            total_runs=Count('id')
        )
        
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
        
        # Weekly totals
        weekly_totals = queryset.aggregate(
            total_production=Sum('good_products_pack'),
            total_downtime=Sum('total_downtime_minutes'),
            avg_oee=Avg('report__oee'),
            total_runs=Count('id')
        )
        
        return {
            'week_start': week_start_date,
            'week_end': week_end_date,
            'daily_summaries': daily_summaries,
            'weekly_totals': weekly_totals,
            'production_line': production_line
        }
    
    @staticmethod
    def get_top_downtime_reasons(start_date: date, end_date: date, 
                                production_line: Optional[ProductionLine] = None, limit: int = 10) -> List[Dict]:
        """Get top downtime reasons for a date range"""
        
       
        
        queryset = StopEvent.objects.filter(
            production_run__date__range=[start_date, end_date]
        )
        
        if production_line:
            queryset = queryset.filter(production_run__production_line=production_line)
        
        downtime_analysis = queryset.values('code','code__reason', 'reason', 'machine__machine_name').annotate(
            total_duration=Sum('duration_minutes'),
            occurrence_count=Count('id')
        ).order_by('-total_duration')[:limit]
        
        return list(downtime_analysis)
    
    @staticmethod
    def calculate_oee_trend(start_date: date, end_date: date, 
                          production_line: Optional[ProductionLine] = None) -> List[Dict]:
        """Calculate OEE trend over a date range"""
        
        queryset = ProductionReport.objects.filter(
            production_run__date__range=[start_date, end_date]
        )
        
        if production_line:
            queryset = queryset.filter(production_run__production_line=production_line)
        
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
                                            production_line: Optional[ProductionLine] = None) -> Dict:
        """Generate comprehensive production efficiency report"""
        
        # Base metrics
        base_data = {
            'period': {
                'start_date': start_date,
                'end_date': end_date,
                'production_line': production_line.name if production_line else 'All Lines'
            }
        }
        
        # OEE Analysis
        base_data['oee_analysis'] = ProductionCalculationService.calculate_oee_trend(
            start_date, end_date, production_line
        )
        
        # Downtime Analysis
        base_data['downtime_analysis'] = ProductionCalculationService.get_top_downtime_reasons(
            start_date, end_date, production_line
        )
        
        # Production Summary
        queryset = ProductionRun.objects.filter(
            date__range=[start_date, end_date]
        )
        if production_line:
            queryset = queryset.filter(production_line=production_line)
        
        base_data['production_summary'] = queryset.aggregate(
            total_production=Sum('good_products_pack'),
            total_downtime=Sum('total_downtime_minutes'),
            avg_oee=Avg('report__oee'),
            total_runs=Count('id')
        )
        
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
            
            total_planned_time = sum([run.planned_production_time_minutes for run in runs])
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
            
            categories.append(f"{item['code']} - {code_reason}")
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
