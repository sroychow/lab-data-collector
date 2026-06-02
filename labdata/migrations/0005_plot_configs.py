from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('labdata', '0004_multiple_tables_and_results'),
    ]

    operations = [
        migrations.CreateModel(
            name='PlotConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('chart_type', models.CharField(choices=[('scatter', 'Scatter'), ('line', 'Line'), ('bar', 'Bar')], default='scatter', max_length=20)),
                ('x_label', models.CharField(blank=True, max_length=120)),
                ('y_label', models.CharField(blank=True, max_length=120)),
                ('description', models.TextField(blank=True)),
                ('active', models.BooleanField(default=True)),
                ('order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('table', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='plot_configs', to='labdata.experimenttable')),
                ('x_field', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='plots_as_x', to='labdata.datafield')),
                ('y_field', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='plots_as_y', to='labdata.datafield')),
            ],
            options={
                'ordering': ['order', 'id'],
            },
        ),
    ]
