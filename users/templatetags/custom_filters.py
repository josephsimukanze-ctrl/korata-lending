from django import template

register = template.Library()

@register.filter
def replace(value, arg):
    """Replace all occurrences of arg with empty string"""
    args = arg.split('|')
    if len(args) == 2:
        return value.replace(args[0], args[1])
    return value.replace(arg, '')