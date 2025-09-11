from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from manufacturing.admin import manufacturing_admin_site

urlpatterns = [
    path("admin/", admin.site.urls),
    path("production-admin/", manufacturing_admin_site.urls),  # Custom production admin - this will be removed later.
    path('accounts/', include('accounts.urls')),
    path('', include('home.urls')),
    path('manufacturing/', include('manufacturing.urls')),    
]


if settings.DEBUG:
    # Include django_browser_reload URLs only in DEBUG mode
    urlpatterns += [
        path("__reload__/", include("django_browser_reload.urls")),
    ]