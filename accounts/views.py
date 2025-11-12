from django.shortcuts import render
from django.urls import reverse_lazy
from allauth.account.views import LoginView, SignupView, ConfirmEmailView, EmailVerificationSentView,LogoutView
from django.contrib import messages
from allauth.account.internal import flows
from allauth.core.exceptions import ImmediateHttpResponse


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
        self.user, resp = form.try_save(self.request)
        if resp:
            return resp
        # Deactivate account pending admin approval
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        messages.success(self.request, 'Account created successfully! Your account is pending admin approval.')
        try:
            redirect_url = self.get_success_url()
            return flows.signup.complete_signup(
                self.request,
                user=self.user,
                redirect_url=redirect_url,
                by_passkey=getattr(form, "by_passkey", False),
            )
        except ImmediateHttpResponse as e:
            return e.response
    

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
