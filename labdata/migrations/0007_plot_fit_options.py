from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("labdata", "0006_alter_observationrow_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="plotconfig",
            name="fit_type",
            field=models.CharField(
                choices=[
                    ("none", "No fit"),
                    ("linear", "Linear fit: y = m x + c"),
                ],
                default="none",
                help_text="Choose Linear fit for graphs expected to follow y = m x + c.",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="plotconfig",
            name="show_fit_equation",
            field=models.BooleanField(default=True),
        ),
    ]
