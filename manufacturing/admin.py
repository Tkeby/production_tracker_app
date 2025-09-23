from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.db.models import Sum, Avg
from .models import (
    ProductionLine, Product, PackageSize, Shift, Machine, DowntimeCode,
    ProductionRun, PackagingMaterial, Utility, 
    StopEvent, ProductionReport
)
from reports.services import ProductionCalculationService


# ===== INLINE ADMIN CLASSES =====

class MachineInline(admin.TabularInline):
    model = Machine
    extra = 0
    fields = ['machine_name', 'machine_code', 'rated_output', 'is_active']


class DowntimeCodeInline(admin.TabularInline):
    model = DowntimeCode
    extra = 0
    fields = ['code', 'reason']


class StopEventInline(admin.TabularInline):
    model = StopEvent
    extra = 0
    fields = ['machine', 'code', 'reason','is_planned', 'duration_minutes', 'timestamp']
    readonly_fields = ['timestamp']


class PackagingMaterialInline(admin.StackedInline):
    model = PackagingMaterial
    extra = 0
    fieldsets = (
        ('Materials Used', {
            'fields': (
                ('qty_preform_used', 'qty_cap_used'),
                ('shrink_wrap_kg', 'stretch_wrap_g', 'label_reject_g')
            )
        }),
        ('Rejects', {
            'fields': (
                ('qty_product_reject', 'qty_preform_reject'),
                ('qty_bottle_reject', 'qty_cap_reject')
            )
        }),
    )


class UtilityInline(admin.StackedInline):
    model = Utility
    extra = 0
    fields = [
        ('kg_co2',), 
        ('boiler_fuel_l', 'generator_fuel_l'),
        ('edg_power_consumption',)
    ]


class ProductionReportInline(admin.StackedInline):
    model = ProductionReport
    extra = 0
    readonly_fields = [
        'syrup_yield_percentage', 'preform_yield_percentage', 'bottle_reject_percentage',
        'availability', 'performance', 'quality', 'oee', 'oee_grade_display', 'calculated_at'
    ]
    
    fieldsets = (
        ('Yield Metrics', {
            'fields': (
                ('syrup_yield_percentage', 'preform_yield_percentage'),
                ('bottle_reject_percentage', 'label_reject_percentage'),
            )
        }),
        ('OEE Analysis', {
            'fields': (
                ('availability', 'performance', 'quality'),
                ('oee', 'oee_grade_display'),
            )
        }),
        ('Utility Metrics', {
            'fields': (
                ('co2_utilization_percentage', 'shrink_wrap_percentage'),
            )
        }),
        ('Metadata', {
            'fields': ('calculated_at',)
        })
    )
    
    def oee_grade_display(self, obj):
        if obj and obj.oee:
            grade = obj.oee_grade
            color_map = {
                'World Class': 'green',
                'Good': 'blue', 
                'Fair': 'orange',
                'Poor': 'red',
                'No Data': 'gray'
            }
            color = color_map.get(grade, 'gray')
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color, grade
            )
        return "Not calculated"
    oee_grade_display.short_description = "OEE Grade"


# ===== MAIN ADMIN CLASSES =====

@admin.register(ProductionLine)
class ProductionLineAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'machine_count', 'is_active', 'rated_speed']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    inlines = [MachineInline]
    
    def machine_count(self, obj):
        return obj.machine_set.count()
    machine_count.short_description = "Machines"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'product_code', 'standard_syrup_ratio']
    search_fields = ['name', 'product_code']
    list_filter = ['standard_syrup_ratio']


@admin.register(PackageSize)
class PackageSizeAdmin(admin.ModelAdmin):
    list_display = ['size', 'package_type', 'volume_ml']
    list_filter = ['package_type']
    search_fields = ['size']


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ['get_name_display', 'start_time', 'end_time', 'duration_hours']
    list_filter = ['name']


@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ['machine_name', 'machine_code', 'production_line', 'rated_output', 'is_active']
    list_filter = ['production_line', 'is_active']
    search_fields = ['machine_name', 'machine_code']
    inlines = [DowntimeCodeInline]


@admin.register(DowntimeCode)
class DowntimeCodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'machine', 'reason']
    list_filter = ['machine__production_line', 'machine']
    search_fields = ['code', 'reason']




@admin.register(ProductionRun)
class ProductionRunAdmin(admin.ModelAdmin):
    list_display = [
        'production_batch_number', 'product', 'package_size', 'production_line',
        'date', 'shift_teamleader', 'good_products_pack', 'oee_display', 'is_completed'
    ]
    list_filter = [
        'is_completed', 'production_line', 'product', 'date', 'shift__name'
    ]
    search_fields = [
        'production_batch_number', 'product__name', 'shift_teamleader__email'
    ]
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                ('production_batch_number',),
                ('date', 'production_line'),
                ('product', 'package_size'),
            )
        }),
        ('Schedule', {
            'fields': (
                ('production_start', 'production_end'),
                ('shift_teamleader', 'shift'),
            )
        }),
        ('Production Data', {
            'fields': (
                ('final_syrup_volume', 'mixing_ratio'),
                ('filler_output', 'good_products_pack'),
                ('total_downtime_minutes',),
            )
        }),
        ('Status', {
            'fields': ('is_completed',)
        })
    )
    
    inlines = [StopEventInline, PackagingMaterialInline, UtilityInline, ProductionReportInline]
    
    actions = ['calculate_reports', 'mark_completed', 'generate_summary_report']
    
    def oee_display(self, obj):
        if hasattr(obj, 'report') and obj.report.oee:
            oee_value = float(obj.report.oee)
            grade = obj.report.oee_grade
            
            color_map = {
                'World Class': '#28a745',
                'Good': '#007bff', 
                'Fair': '#ffc107',
                'Poor': '#dc3545',
                'No Data': '#6c757d'
            }
            color = color_map.get(grade, '#6c757d')
            oee_str = f"{oee_value:.1f}"
            
            return format_html(
                '<span style="background-color: {}; color: white; padding: 2px 8px; '
                'border-radius: 3px; font-size: 11px; font-weight: bold;">{}%</span>',
                color, oee_str
            )
        return format_html('<span style="color: #6c757d;">Not calculated</span>')
    oee_display.short_description = "OEE"
    
    def calculate_reports(self, request, queryset):
        """Admin action to calculate reports for selected production runs"""
        calculated_count = 0
        for production_run in queryset:
            try:
                production_run.update_calculations()
                calculated_count += 1
            except Exception as e:
                messages.error(request, f"Error calculating {production_run}: {e}")
        
        messages.success(request, f"Successfully calculated reports for {calculated_count} production runs.")
    calculate_reports.short_description = "Calculate production reports"
    
    def mark_completed(self, request, queryset):
        """Mark selected production runs as completed and calculate reports"""
        updated = queryset.update(is_completed=True)
        for production_run in queryset:
            production_run.update_calculations()
        
        messages.success(request, f"Marked {updated} production runs as completed and calculated reports.")
    mark_completed.short_description = "Mark as completed and calculate reports"
    
    def generate_summary_report(self, request, queryset):
        """Generate summary report for selected production runs"""
        if not queryset:
            messages.warning(request, "No production runs selected.")
            return
            
        # This would redirect to a custom report view
        selected_ids = list(queryset.values_list('id', flat=True))
        return HttpResponseRedirect(
            reverse('admin:manufacturing_summary_report') + f"?ids={','.join(map(str, selected_ids))}"
        )
    generate_summary_report.short_description = "Generate summary report"


@admin.register(StopEvent)
class StopEventAdmin(admin.ModelAdmin):
    list_display = [
        'production_run', 'machine', 'code', 'duration_minutes', 'timestamp'
    ]
    list_filter = ['machine', 'code', 'timestamp', 'production_run__production_line']
    search_fields = ['machine', 'code', 'reason', 'production_run__production_batch_number']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Event Details', {
            'fields': ('production_run', 'machine', 'code', 'is_planned')
        }),
        ('Duration & Details', {
            'fields': ('duration_minutes', 'reason', 'timestamp')
        })
    )
    
    readonly_fields = ['timestamp']


@admin.register(ProductionReport)
class ProductionReportAdmin(admin.ModelAdmin):
    list_display = [
        'production_run', 'oee_display', 'availability_display', 
        'performance_display', 'quality_display', 'calculated_at'
    ]
    list_filter = [
        'production_run__production_line', 'production_run__date', 'calculated_at'
    ]
    search_fields = ['production_run__production_batch_number']
    date_hierarchy = 'calculated_at'
    
    fieldsets = (
        ('Production Run', {
            'fields': ('production_run',)
        }),
        ('Yield Metrics', {
            'fields': (
                ('syrup_yield_percentage', 'preform_yield_percentage'),
                ('bottle_reject_percentage', 'label_reject_percentage'),
            )
        }),
        ('OEE Analysis', {
            'fields': (
                ('availability', 'performance', 'quality'),
                ('oee',),
            )
        }),
        ('Utility Metrics', {
            'fields': (
                ('co2_utilization_percentage', 'shrink_wrap_percentage'),
            )
        }),
    )
    
    readonly_fields = ['calculated_at']
    
    def oee_display(self, obj):
        if obj.oee:
            grade = obj.oee_grade
            color_map = {
                'World Class': '#28a745',
                'Good': '#007bff', 
                'Fair': '#ffc107',
                'Poor': '#dc3545',
                'No Data': '#6c757d'
            }
            color = color_map.get(grade, '#6c757d')
            oee_str = f"{float(obj.oee):.1f}"
            return format_html(
                '<div style="text-align: center;">'
                '<div style="background-color: {}; color: white; padding: 4px; '
                'border-radius: 4px; margin-bottom: 2px; font-weight: bold;">{}%</div>'
                '<small style="color: {};">{}</small></div>',
                color, oee_str, color, grade
            )
        return "Not calculated"
    oee_display.short_description = "OEE"
    
    def availability_display(self, obj):
        return self._percentage_display(obj.availability, 'Availability')
    availability_display.short_description = "Availability"
    
    def performance_display(self, obj):
        return self._percentage_display(obj.performance, 'Performance')
    performance_display.short_description = "Performance"
    
    def quality_display(self, obj):
        return self._percentage_display(obj.quality, 'Quality')
    quality_display.short_description = "Quality"
    
    def _percentage_display(self, value, label):
        if value is not None:
            color = '#28a745' if value >= 85 else '#007bff' if value >= 70 else '#ffc107' if value >= 50 else '#dc3545'
            value_str = f"{float(value):.1f}"
            return format_html('<span style="color: {}; font-weight: bold;">{}%</span>', color, value_str)
        return "N/A"


# ===== CUSTOM ADMIN SITE CONFIGURATION =====

class ManufacturingAdminSite(admin.AdminSite):
    site_header = 'Production Management System'
    site_title = 'Production Admin'
    index_title = 'Production Management Dashboard'
    
    def index(self, request, extra_context=None):
        """Custom admin index with production dashboard"""
        from django.utils import timezone
        from datetime import timedelta
        
        extra_context = extra_context or {}
        
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        
        # Get today's production summary
        today_runs = ProductionRun.objects.filter(date=today)
        today_summary = today_runs.aggregate(
            total_production=Sum('good_products_pack'),
            total_downtime=Sum('total_downtime_minutes'),
            avg_oee=Avg('report__oee'),
            runs_count=Sum('id')
        )
        
        # Get alerts
        alerts = ProductionCalculationService.get_production_alerts()
        
        # Recent completed production runs
        recent_completed = ProductionRun.objects.filter(
            is_completed=True
        ).order_by('-updated_at')[:5]
        
        # Active production runs
        active_runs = ProductionRun.objects.filter(
            is_completed=False
        ).count()
        
        extra_context.update({
            'today_summary': today_summary,
            'alerts': alerts[:10],  # Show top 10 alerts
            'recent_completed': recent_completed,
            'active_runs': active_runs,
            'today_date': today,
        })
        
        return super().index(request, extra_context)


# Create custom admin site instance
manufacturing_admin_site = ManufacturingAdminSite(name='manufacturing_admin')

# Register all models with the custom admin site
manufacturing_admin_site.register(ProductionLine, ProductionLineAdmin)
manufacturing_admin_site.register(Product, ProductAdmin)
manufacturing_admin_site.register(PackageSize, PackageSizeAdmin)
manufacturing_admin_site.register(Shift, ShiftAdmin)
manufacturing_admin_site.register(Machine, MachineAdmin)
manufacturing_admin_site.register(DowntimeCode, DowntimeCodeAdmin)
manufacturing_admin_site.register(ProductionRun, ProductionRunAdmin)
manufacturing_admin_site.register(StopEvent, StopEventAdmin)
manufacturing_admin_site.register(ProductionReport, ProductionReportAdmin)
