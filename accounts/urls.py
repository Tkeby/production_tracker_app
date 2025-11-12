from django.urls import path, include
from . import views

urlpatterns = [
    # Custom authentication views (using allauth's expected URL names)
    path('login/', views.CustomLoginView.as_view(), name='account_login'),
    # path('signup/', views.CustomSignupView.as_view(), name='account_signup'),
    path('confirm-email/', views.CustomEmailVerificationSentView.as_view(), name='account_email_verification_sent'),
    path('confirm-email/<str:key>/', views.CustomConfirmEmailView.as_view(), name='account_confirm_email'),
    
    # Include remaining allauth URLs (logout, password reset, etc.)
    path('', include('allauth.urls')),
]