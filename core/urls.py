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


if settings.DEBUG:
    # Include django_browser_reload URLs only in DEBUG mode
    urlpatterns += [
        path("__reload__/", include("django_browser_reload.urls")),
    ]
    # Serve static and media files during development
    urlpatterns += static(settings.STATIC_URL, document_root=getattr(settings, 'STATIC_ROOT', None))
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)