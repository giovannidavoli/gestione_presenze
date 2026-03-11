from django import template
register = template.Library()

@register.filter
def dict_key(value, arg):
    """Permette di accedere alle chiavi del dizionario mapping_fields."""
    return value.get(arg)