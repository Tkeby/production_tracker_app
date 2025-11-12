from django.shortcuts import render
from django.urls import reverse_lazy
from allauth.account.views import LoginView, SignupView, ConfirmEmailView, EmailVerificationSentView,LogoutView
from django.contrib import messages
from allauth.account.internal import flows
from allauth.core.exceptions import ImmediateHttpResponse


    # myproject/adapters.py
from allauth.account.adapter import DefaultAccountAdapter

class CustomAccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        """
        Prevents new users from signing up.
        """
        return False

class CustomLoginView(LoginView):
    """Custom login view extending allauth's LoginView"""
    template_name = 'accounts/login.html'
    success_url = reverse_lazy('manufacturing:dashboard')  # Home page
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Login'
        return context
    
    def form_valid(self, form):
        # Get user before calling super() since request.user is still AnonymousUser at this point
        user = form.user
        response = super().form_valid(form)
        messages.success(self.request, f'Welcome back, {user.email}!')
        return response


class CustomSignupView(SignupView):
    """Custom signup view extending allauth's SignupView"""  
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('manufacturing:dashboard')  # Home page
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Sign Up'
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Account created successfully! Please check your email to verify your account.')
        return response

    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        user.is_active = False  # Set user to inactive initially
        if commit:
            user.save()
        return user


class CustomConfirmEmailView(ConfirmEmailView):
    """Custom email confirmation view extending allauth's ConfirmEmailView"""
    template_name = 'accounts/confirm_email.html'
    success_url = reverse_lazy('manufacturing:dashboard')  # Redirect after successful confirmation
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Confirm Email'
        return context
    
    def post(self, *args, **kwargs):
        response = super().post(*args, **kwargs)
        # Only show success message if confirmation was successful
        if hasattr(self, 'object') and self.object:
            messages.success(self.request, 'Email confirmed successfully! Your account is now fully activated.')
        return response


class CustomEmailVerificationSentView(EmailVerificationSentView):
    """Custom email verification sent view extending allauth's EmailVerificationSentView"""
    template_name = 'accounts/verification_sent.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Check Your Email'
        # Add user email if available for display
        if self.request.user.is_authenticated:
            context['user_email'] = self.request.user.email
        return context
