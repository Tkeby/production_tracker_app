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
    path('reports/', views.ReportsListView.as_view(), name='reports_list'),
    
    # HTMX endpoints
    path('htmx/product-info/', views.htmx_product_info, name='htmx_product_info'),
    path('htmx/product-packages/', views.htmx_product_packages, name='htmx_product_packages'),
    path('htmx/machine-codes/', views.htmx_machine_codes, name='htmx_machine_codes'),
]