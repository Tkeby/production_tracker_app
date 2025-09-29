from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from manufacturing.admin import manufacturing_admin_site

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),  # Dynamic admin URL for security
    path("production-admin/", manufacturing_admin_site.urls),  # Custom production admin - this will be removed later.
    path('accounts/', include('accounts.urls')),
    path('', include('home.urls')),
    path('manufacturing/', include('manufacturing.urls')),    
    path('reports/', include('reports.urls')),    
]

# Custom error handlers
handler404 = 'core.error_views.custom_404_view'
handler500 = 'core.error_views.custom_500_view'
handler403 = 'core.error_views.custom_403_view'
handler400 = 'core.error_views.custom_400_view'


if settings.DEBUG:
    # Include django_browser_reload URLs only in DEBUG mode
    urlpatterns += [
        path("__reload__/", include("django_browser_reload.urls")),
    ]
    # Serve static and media files during development
    urlpatterns += static(settings.STATIC_URL, document_root=getattr(settings, 'STATIC_ROOT', None))
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)