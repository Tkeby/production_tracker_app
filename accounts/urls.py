from django.urls import path, include
from . import views

urlpatterns = [
    # Custom authentication views (using allauth's expected URL names)
    path('login/', views.CustomLoginView.as_view(), name='account_login'),
    path('signup/', views.CustomSignupView.as_view(), name='account_signup'),
    
    # Include remaining allauth URLs (logout, password reset, etc.)
    path('', include('allauth.urls')),
]