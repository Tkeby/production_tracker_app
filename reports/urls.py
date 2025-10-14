from django.urls import path
from . import views

from . import pdf_views


app_name = 'reports'

urlpatterns = [
    # Dashboard and overview
    path('', views.ReportsDashboardView.as_view(), name='dashboard'),
    
    # Summary Reports
    path('daily-summary/', views.DailySummaryView.as_view(), name='daily_summary'),
    path('weekly-summary/', views.WeeklySummaryView.as_view(), name='weekly_summary'),
    
    # PDF Reports
    path('shift-summary/pdf/', pdf_views.ShiftSummaryPDFView.as_view(), name='shift_summary_pdf'),
    path('weekly-summary/pdf/', pdf_views.WeeklySummaryPDFView.as_view(), name='weekly_summary_pdf'),
    
    # Analysis Reports
   
    path('oee-trend/', views.OEETrendView.as_view(), name='oee_trend'),
    path('downtime-details/', views.DowntimeDetailsView.as_view(), name='downtime_details'),
    
    path('machine-utilization/', views.MachineUtilizationView.as_view(), name='machine_utilization'),
   
    # HTMX endpoints for dynamic content
    path('htmx/alerts/', views.production_alerts_htmx, name='alerts_htmx'),
    path('htmx/daily-summary/<str:date>/', views.daily_summary_htmx, name='daily_summary_htmx'),
    path('htmx/oee-chart/<str:start_date>/<str:end_date>/', views.oee_chart_htmx, name='oee_chart_htmx'),
    path('htmx/machines-by-line/', views.machines_by_production_line_htmx, name='machines_by_line_htmx'),
]
