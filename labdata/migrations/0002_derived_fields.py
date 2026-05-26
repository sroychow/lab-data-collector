from django.db import migrations, models
from django.utils.text import slugify


def populate_variable_names(apps, schema_editor):
    DataField = apps.get_model('labdata', 'DataField')
    used_by_experiment = {}
    for field in DataField.objects.all().order_by('experiment_id', 'order', 'id'):
        used = used_by_experiment.setdefault(field.experiment_id, set())
        base = (slugify(field.name).replace('-', '_')[:70] or 'field')
        if base[0].isdigit():
            base = f'f_{base}'
        variable = base
        counter = 2
        while variable in used:
            variable = f'{base}_{counter}'
            counter += 1
        field.variable_name = variable
        field.save(update_fields=['variable_name'])
        used.add(variable)


class Migration(migrations.Migration):

    dependencies = [
        ('labdata', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='datafield',
            name='variable_name',
            field=models.SlugField(
                blank=True,
                help_text='Formula variable name, for example length, time_period, theta. Auto-filled from the field name if blank.',
                max_length=80,
            ),
        ),
        migrations.AddField(
            model_name='datafield',
            name='calculation_formula',
            field=models.CharField(
                blank=True,
                help_text='Only for derived fields. Examples: length/time, 2*pi*r, m*g*h, sin(theta*pi/180), sqrt(x**2+y**2).',
                max_length=500,
            ),
        ),
        migrations.RunPython(populate_variable_names, migrations.RunPython.noop),
    ]
