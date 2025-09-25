from django.contrib import admin
from django.urls import path, include
from . import views

app_name = 'manufacturing'

urlpatterns = [
    path("admin/", admin.site.urls),
    
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('production-run/create/', views.CreateProductionRunView.as_view(), name='create_production_run'),
    path('production-run/<int:pk>/', views.ProductionRunDetailView.as_view(), name='production_run_detail'),
    path('production-run/<int:pk>/edit/', views.UpdateProductionRunView.as_view(), name='update_production_run'),
    path('production-run/<int:pk>/finalize/', views.FinalizeProductionRunView.as_view(), name='finalize_production_run'),
    path('production-run/<int:production_run_pk>/add-stop-event/', views.CreateStopEventView.as_view(), name='create_stop_event'),
    path('stop-event/<int:pk>/edit/', views.UpdateStopEventView.as_view(), name='update_stop_event'),
    path('stop-event/<int:pk>/delete/', views.DeleteStopEventView.as_view(), name='delete_stop_event'),
    path('reports/', views.ReportsListView.as_view(), name='reports_list'),
    
    # HTMX endpoints
    path('htmx/product-packages/', views.htmx_product_packages, name='htmx_product_packages'),
    path('htmx/machine-codes/', views.htmx_machine_codes, name='htmx_machine_codes'),
    path('htmx/packaging-fields/', views.htmx_packaging_fields, name='htmx_packaging_fields'),
    path('htmx/generate-batch-number/', views.htmx_generate_batch_number, name='htmx_generate_batch_number'),
    path('htmx/stop-event/<int:production_run_pk>/', views.htmx_create_stop_event, name='htmx_create_stop_event'),
    path('htmx/recent-stop-events/<int:production_run_pk>/', views.htmx_recent_stop_events, name='htmx_recent_stop_events'),
    path('htmx/downtime-badge/<int:production_run_pk>/', views.htmx_downtime_badge, name='htmx_downtime_badge'),
]