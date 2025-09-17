from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Dashboard and overview
    path('', views.ReportsDashboardView.as_view(), name='dashboard'),
    
    # Summary Reports
    path('shift-summary/', views.ShiftSummaryView.as_view(), name='shift_summary'),
    path('daily-summary/', views.DailySummaryView.as_view(), name='daily_summary'),
    path('weekly-summary/', views.WeeklySummaryView.as_view(), name='weekly_summary'),
    
    # Analysis Reports
    path('efficiency-report/', views.ProductionEfficiencyReportView.as_view(), name='efficiency_report'),
    path('oee-trend/', views.OEETrendView.as_view(), name='oee_trend'),
    path('downtime-analysis/', views.DowntimeAnalysisView.as_view(), name='downtime_analysis'),
    path('machine-utilization/', views.MachineUtilizationView.as_view(), name='machine_utilization'),
    
    # HTMX endpoints for dynamic content
    path('htmx/alerts/', views.production_alerts_htmx, name='alerts_htmx'),
    path('htmx/daily-summary/<str:date>/', views.daily_summary_htmx, name='daily_summary_htmx'),
    path('htmx/oee-chart/<str:start_date>/<str:end_date>/', views.oee_chart_htmx, name='oee_chart_htmx'),
]
