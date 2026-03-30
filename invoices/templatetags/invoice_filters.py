from django import template

register = template.Library()


@register.filter(name='dict_get')
def dict_get(d, key):
    if isinstance(d, dict):
        return d.get(key, 0)
    return 0


@register.filter(name='abs_value')
def abs_value(value):
    try:
        return abs(value)
    except (TypeError, ValueError):
        return value
