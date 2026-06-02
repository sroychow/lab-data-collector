from django import template

register = template.Library()


@register.filter
def field_value(row, field):
    for value in row.values.all():
        if value.field_id == field.id:
            return value.value
    return ''
