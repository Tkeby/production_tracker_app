from django import template

register = template.Library()

@register.filter
def lookup(dictionary, key):
    """Custom template filter to lookup dictionary values by key"""
    if dictionary is None:
        return None
    try:
        return dictionary.get(key, 0)
    except (AttributeError, TypeError):
        return 0
