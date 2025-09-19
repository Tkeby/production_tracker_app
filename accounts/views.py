from django.shortcuts import render
from django.urls import reverse_lazy
from allauth.account.views import LoginView, SignupView
from django.contrib import messages


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
