# Migration to add multiple observation tables and final result fields.
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion
from django.utils.text import slugify


def _safe_var(text, fallback):
    base = slugify(text or fallback).replace('-', '_')[:70] or fallback
    if base[0].isdigit():
        base = f't_{base}'
    return base


def create_default_tables(apps, schema_editor):
    Experiment = apps.get_model('labdata', 'Experiment')
    ExperimentTable = apps.get_model('labdata', 'ExperimentTable')
    DataField = apps.get_model('labdata', 'DataField')
    ObservationRow = apps.get_model('labdata', 'ObservationRow')

    default_by_experiment = {}
    for experiment in Experiment.objects.all():
        table, _ = ExperimentTable.objects.get_or_create(
            experiment=experiment,
            variable_name='main',
            defaults={
                'name': 'Main observations',
                'description': 'Default table created automatically during the multiple-table migration.',
                'order': 0,
            },
        )
        default_by_experiment[experiment.id] = table

    for field in DataField.objects.all():
        table = default_by_experiment.get(field.experiment_id)
        if table:
            field.table_id = table.id
            field.save(update_fields=['table'])

    for row in ObservationRow.objects.select_related('submission').all():
        table = default_by_experiment.get(row.submission.experiment_id)
        if table:
            row.table_id = table.id
            row.save(update_fields=['table'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('labdata', '0003_alter_datafield_field_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExperimentTable',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=160)),
                ('variable_name', models.SlugField(help_text='Short table name used in formulas, e.g. length, time, calibration.', max_length=80)),
                ('description', models.TextField(blank=True)),
                ('order', models.PositiveIntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ('experiment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tables', to='labdata.experiment')),
            ],
            options={
                'ordering': ['order', 'id'],
                'unique_together': {('experiment', 'variable_name')},
            },
        ),
        migrations.CreateModel(
            name='ResultField',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=160)),
                ('variable_name', models.SlugField(blank=True, help_text='Result variable name. Later result formulas can use this name.', max_length=80)),
                ('calculation_formula', models.CharField(help_text='Examples: mean(length.lmean), mean(time.t20)/20, 4*pi**2*L/(T**2).', max_length=1000)),
                ('unit', models.CharField(blank=True, max_length=40)),
                ('help_text', models.CharField(blank=True, max_length=240)),
                ('order', models.PositiveIntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ('experiment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='result_fields', to='labdata.experiment')),
            ],
            options={
                'ordering': ['order', 'id'],
                'unique_together': {('experiment', 'variable_name')},
            },
        ),
        migrations.CreateModel(
            name='ResultValue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.TextField(blank=True)),
                ('result_field', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='labdata.resultfield')),
                ('submission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='result_values', to='labdata.submission')),
            ],
            options={
                'unique_together': {('submission', 'result_field')},
            },
        ),
        migrations.AddField(
            model_name='datafield',
            name='table',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='fields', to='labdata.experimenttable'),
        ),
        migrations.AddField(
            model_name='observationrow',
            name='table',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='rows', to='labdata.experimenttable'),
        ),
        migrations.RunPython(create_default_tables, noop_reverse),
        migrations.AlterField(
            model_name='datafield',
            name='table',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fields', to='labdata.experimenttable'),
        ),
        migrations.AlterField(
            model_name='observationrow',
            name='table',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rows', to='labdata.experimenttable'),
        ),
        migrations.AlterUniqueTogether(
            name='datafield',
            unique_together={('table', 'name'), ('table', 'variable_name')},
        ),
        migrations.AlterUniqueTogether(
            name='observationrow',
            unique_together={('submission', 'table', 'serial_number')},
        ),
    ]
