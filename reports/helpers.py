from django.db.models import Sum, Avg, Count, Case, When
from decimal import Decimal
from typing import Dict, Optional, List
from manufacturing.models import ProductionRun, ProductionLine, StopEvent


def filter_production_runs(shift_date, production_line: Optional[ProductionLine] = None, 
                          shift_type: Optional[str] = None):
    """Common queryset filtering logic for production runs"""
    queryset = ProductionRun.objects.filter(date=shift_date)
    
    if production_line:
        queryset = queryset.filter(production_line=production_line)
    
    if shift_type:
        queryset = queryset.filter(shift__name=shift_type)
    
    return queryset


def aggregate_production_totals(queryset) -> Dict:
    """Aggregate basic production metrics from a queryset"""
    return queryset.aggregate(
        total_production=Sum('good_products_pack'),
        total_downtime=Sum('total_downtime_minutes'),
        avg_oee=Avg('report__oee'),
        production_runs_count=Count('id'),
        total_syrup=Sum('final_syrup_volume')
    )


def aggregate_basic_totals(queryset) -> Dict:
    """Aggregate simplified production totals for daily/weekly summaries"""
    return queryset.aggregate(
        total_production=Sum('good_products_pack'),
        total_downtime=Sum('total_downtime_minutes'),
        avg_oee=Avg('report__oee'),
        total_runs=Count('id')
    )


def aggregate_production_by_line(queryset) -> List[Dict]:
    """Get production breakdown by production line"""
    production_by_line = queryset.values('production_line__name').annotate(
        line_production=Sum('good_products_pack')
    )
    
    # Convert to list and sort by custom order
    line_data = list(production_by_line)
    
    # Define preferred order
    line_order = {
        'Line A': 1,
        'Line B': 2, 
        'Line C': 3,
        'Line CAN': 4
    }
    
    # Sort by custom order, fallback to alphabetical for unknown lines
    def sort_key(item):
        line_name = item['production_line__name']
        return line_order.get(line_name, 999), line_name
    
    line_data.sort(key=sort_key)
    
    return line_data


def aggregate_stop_events(queryset) -> Dict:
    """Aggregate planned and unplanned downtime from stop events"""
    stop_events_qs = StopEvent.objects.filter(production_run__in=queryset)
    return stop_events_qs.aggregate(
        total_unplanned_downtime=Sum(
            Case(
                When(is_planned=False, then='duration_minutes'),
                default=0
            )
        ),
        total_planned_downtime=Sum(
            Case(
                When(is_planned=True, then='duration_minutes'),
                default=0
            )
        )
    )


def calculate_total_planned_time(queryset) -> Decimal:
    """Calculate total planned production time from queryset"""
    return sum([Decimal(str(run.planned_production_time_minutes)) for run in queryset])


def calculate_availability_percentage(total_planned_time: Decimal, total_downtime: Optional[int]) -> float:
    """Calculate availability percentage from planned time and downtime"""
    if total_planned_time > 0:
        return ((total_planned_time - (total_downtime or 0)) / total_planned_time * 100)
    return 0.0


def build_production_summary(queryset, production_line: Optional[ProductionLine] = None) -> Dict:
    """Build comprehensive production summary with common metrics"""
    # Get basic production aggregation
    if production_line is None:
        # Multi-line summary with breakdown
        run_totals = aggregate_production_totals(queryset)
        production_by_line = aggregate_production_by_line(queryset)
        run_totals['production_by_line'] = production_by_line
    else:
        # Single line summary
        run_totals = aggregate_production_totals(queryset)
    
    # Get stop events aggregation
    stop_agg = aggregate_stop_events(queryset)
    
    # Merge summaries
    summary = {**run_totals, **stop_agg}
    
    # Calculate additional metrics
    total_planned_time = calculate_total_planned_time(queryset)
    availability_percentage = calculate_availability_percentage(
        total_planned_time, summary['total_downtime']
    )
    
    summary.update({
        'total_planned_time_minutes': total_planned_time,
        'availability_percentage': availability_percentage,
        'runs': queryset.select_related('product', 'package_size', 'shift_teamleader')
    })
    
    return summary
