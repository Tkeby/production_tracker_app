from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView
from django.views import View
from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponse

from django.contrib import messages

from datetime import date, timedelta

from .pdf_generators import ReportPDFGenerator

from manufacturing.models import ProductionLine, Machine
from .services import ProductionCalculationService
from .mixins import ReportsPermissionMixin, DetailedReportsPermissionMixin
from .forms import (
    ReportFilterForm,  DailySummaryForm, 
    WeeklySummaryForm, MachineUtilizationForm
)


class ReportsDashboardView(ReportsPermissionMixin, TemplateView):
    """Main reports dashboard with key metrics and alerts - Uses Guardian object-level permissions"""
    template_name = 'reports/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get production alerts
        alerts = ProductionCalculationService.get_production_alerts()
        
        # Get today's summary
        today = date.today()
        today_summary = ProductionCalculationService.calculate_daily_summary(today)
        
        # Get week summary
        week_start = today - timedelta(days=today.weekday())
        week_summary = ProductionCalculationService.calculate_weekly_summary(week_start)
        
        # Get OEE trend for last 7 days
        oee_data = ProductionCalculationService.calculate_oee_trend(
            today - timedelta(days=6), today
        )
        oee_trend = oee_data.get('oee_trend', []) if isinstance(oee_data, dict) else oee_data
        
        # Get top downtime reasons for last 7 days
        top_downtime = ProductionCalculationService.get_top_downtime_reasons(
            today - timedelta(days=6), today, limit=5
        )
        
        context.update({
            'alerts': alerts,
            'today_summary': today_summary,
            'week_summary': week_summary,
            'oee_trend': oee_trend,
            'top_downtime': top_downtime,
            'production_lines': ProductionLine.objects.filter(is_active=True)
        })
        
        return context


class DailySummaryView(ReportsPermissionMixin, TemplateView):
    """Shift summary report view"""
    template_name = 'reports/daily_summary.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = DailySummaryForm(self.request.GET or None)
        context['form'] = form
        
        if form.is_valid():
            shift_date = form.cleaned_data['shift_date']
            production_line = form.cleaned_data['production_line']
            shift_type = form.cleaned_data['shift_type']
            
            summary = ProductionCalculationService.calculate_shift_summary(
                shift_date, production_line, shift_type
            )
            context['summary'] = summary
            context['shift_date'] = shift_date
            context['selected_line'] = production_line
            context['selected_shift'] = shift_type
        
        return context


class WeeklySummaryView(ReportsPermissionMixin, TemplateView):
    """Weekly summary report view"""
    template_name = 'reports/weekly_summary.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = WeeklySummaryForm(self.request.GET or None)
        context['form'] = form
        
        if form.is_valid():
            week_start_date = form.cleaned_data['week_start_date']
            production_line = form.cleaned_data['production_line']
            week_end_date = week_start_date + timedelta(days=6)
            
            summary = ProductionCalculationService.calculate_weekly_summary(
                week_start_date, production_line
            )
            context['summary'] = summary
            
            # Calculate product trend for the week
            product_trend = ProductionCalculationService.calculate_product_trend(
                week_start_date, week_end_date, production_line
            )
            context['product_trend'] = product_trend
            
            # Calculate product summary by line/product/package for the week
            product_summary = ProductionCalculationService.calculate_product_summary_by_line_product_package(
                week_start_date, week_end_date, production_line
            )
            context['product_summary'] = product_summary
        
        return context


class OEETrendView(DetailedReportsPermissionMixin, TemplateView):
    """OEE trend analysis view - Requires detailed reports permission"""
    template_name = 'reports/oee_trend.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = ReportFilterForm(self.request.GET or None)
        context['form'] = form
        
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            production_line = form.cleaned_data['production_line']
            machine = form.cleaned_data['machine']
            
            oee_data = ProductionCalculationService.calculate_oee_trend(
                start_date, end_date, production_line, machine
            )
            context['oee_data'] = oee_data
           
        
        return context


class MachineUtilizationView(DetailedReportsPermissionMixin, TemplateView):
    """Machine utilization report view - Requires detailed reports permission"""
    template_name = 'reports/machine_utilization.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = MachineUtilizationForm(self.request.GET or None)
        context['form'] = form
        
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            production_line = form.cleaned_data['production_line']
            
            utilization_data = ProductionCalculationService.calculate_machine_utilization(
                start_date, end_date, production_line
            )
            context['utilization_data'] = utilization_data
            context['production_line'] = production_line
            context['date_range'] = f"{start_date} to {end_date}"
            
            # Calculate summary statistics for template
            if utilization_data:
                total_machines = len(utilization_data)
                avg_utilization = sum(data['utilization_percentage'] for data in utilization_data.values()) / total_machines
                total_planned_time = sum(data['total_planned_time'] for data in utilization_data.values())
                total_downtime = sum(data['total_downtime'] for data in utilization_data.values())
                high_performers = sum(1 for data in utilization_data.values() if data['utilization_percentage'] >= 80)
                needs_attention = sum(1 for data in utilization_data.values() if data['utilization_percentage'] < 70)
                
                # Add actual runtime calculation to each machine's data
                for machine_name, data in utilization_data.items():
                    data['actual_runtime'] = data['total_planned_time'] - data['total_downtime']
                
                context['summary_stats'] = {
                    'avg_utilization': round(avg_utilization, 1),
                    'total_planned_time': total_planned_time,
                    'total_downtime': total_downtime,
                    'high_performers': high_performers,
                    'needs_attention': needs_attention
                }
        
        return context


# HTMX Views for dynamic content
def production_alerts_htmx(request):
    """HTMX endpoint for production alerts"""
    production_line_id = request.GET.get('production_line')
    production_line = None
    
    if production_line_id:
        production_line = get_object_or_404(ProductionLine, id=production_line_id)
    
    alerts = ProductionCalculationService.get_production_alerts(production_line)
    
    return render(request, 'reports/htmx/alerts.html', {
        'alerts': alerts
    })


def daily_summary_htmx(request, date):
    """HTMX endpoint for daily summary"""
    try:
        target_date = date.fromisoformat(date)
    except ValueError:
        return HttpResponse("Invalid date format", status=400)
    
    production_line_id = request.GET.get('production_line')
    production_line = None
    
    if production_line_id:
        try:
            production_line = ProductionLine.objects.get(id=production_line_id, is_active=True)
        except ProductionLine.DoesNotExist:
            pass
    
    summary = ProductionCalculationService.calculate_daily_summary(
        target_date, production_line
    )
    
    return render(request, 'reports/htmx/daily_summary.html', {
        'summary': summary,
        'date': target_date
    })


def oee_chart_htmx(request, start_date, end_date):
    """HTMX endpoint for OEE chart data"""
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except ValueError:
        return JsonResponse({"error": "Invalid date format"}, status=400)
    
    production_line_id = request.GET.get('production_line')
    production_line = None
    
    if production_line_id:
        try:
            production_line = ProductionLine.objects.get(id=production_line_id, is_active=True)
        except ProductionLine.DoesNotExist:
            pass
    
    oee_data = ProductionCalculationService.calculate_oee_trend(
        start, end, production_line
    )
    
    # Extract trend data
    trend_data = oee_data.get('oee_trend', []) if isinstance(oee_data, dict) else oee_data
    
    # Format data for chart
    chart_data = {
        'labels': [item['production_run__date'].strftime('%Y-%m-%d') for item in trend_data],
        'datasets': [
            {
                'label': 'OEE %',
                'data': [float(item['avg_oee'] or 0) for item in trend_data],
                'borderColor': 'rgb(59, 130, 246)',
                'backgroundColor': 'rgba(59, 130, 246, 0.1)',
                'tension': 0.1
            },
            {
                'label': 'Availability %',
                'data': [float(item['avg_availability'] or 0) for item in trend_data],
                'borderColor': 'rgb(16, 185, 129)',
                'backgroundColor': 'rgba(16, 185, 129, 0.1)',
                'tension': 0.1
            },
            {
                'label': 'Performance %',
                'data': [float(item['avg_performance'] or 0) for item in trend_data],
                'borderColor': 'rgb(245, 158, 11)',
                'backgroundColor': 'rgba(245, 158, 11, 0.1)',
                'tension': 0.1
            },
            {
                'label': 'Quality %',
                'data': [float(item['avg_quality'] or 0) for item in trend_data],
                'borderColor': 'rgb(239, 68, 68)',
                'backgroundColor': 'rgba(239, 68, 68, 0.1)',
                'tension': 0.1
            }
        ]
    }
    
    return JsonResponse(chart_data)


def machines_by_production_line_htmx(request):
    """HTMX endpoint to get machine options for a specific production line"""
    production_line_id = request.GET.get('production_line')
    
    machines = []
    if production_line_id:
        try:
            production_line = ProductionLine.objects.get(id=production_line_id, is_active=True)
            machines = Machine.objects.filter(
                production_line=production_line, 
                is_active=True
            ).order_by('machine_name')
        except (ProductionLine.DoesNotExist, ValueError):
            pass
    
    return render(request, 'reports/htmx/machine_options.html', {
        'machines': machines
    })