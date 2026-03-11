from django import template
register = template.Library()

@register.filter
def dict_key(value, arg):
    """Permette di leggere le chiavi del dizionario dei campi nel template."""
    return value.get(arg)