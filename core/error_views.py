"""
Custom error views for Django application
"""
from django.shortcuts import render


def custom_404_view(request, exception):
    """
    Custom 404 error view
    """
    return render(request, '404.html', status=404)


def custom_500_view(request):
    """
    Custom 500 error view
    """
    return render(request, '500.html', status=500)


def custom_403_view(request, exception):
    """
    Custom 403 error view (though we handle this in our mixins)
    """
    return render(request, '403.html', status=403)


def custom_400_view(request, exception):
    """
    Custom 400 bad request error view
    """
    return render(request, '404.html', status=400)  # Use 404 template for simplicity
