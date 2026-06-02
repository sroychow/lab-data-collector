from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify


class Experiment(models.Model):
    STATUS_CHOICES = [('draft', 'Draft'), ('active', 'Active'), ('archived', 'Archived')]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    course_or_project = models.CharField(max_length=200, blank=True)
    objective = models.TextField(blank=True)
    protocol_version = models.CharField(max_length=50, default='v1')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='experiments_created',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:190] or 'experiment'
            slug = base
            i = 2
            while Experiment.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{i}'
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class ExperimentTable(models.Model):
    experiment = models.ForeignKey(
        Experiment,
        on_delete=models.CASCADE,
        related_name='tables',
    )
    name = models.CharField(max_length=160)
    variable_name = models.SlugField(
        max_length=80,
        help_text='Short table name used in formulas, e.g. length, time, calibration.',
    )
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])

    class Meta:
        ordering = ['order', 'id']
        unique_together = [('experiment', 'variable_name')]

    def save(self, *args, **kwargs):
        if not self.variable_name:
            base = slugify(self.name).replace('-', '_')[:70] or 'table'
            if base[0].isdigit():
                base = f't_{base}'
            self.variable_name = base
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.experiment}: {self.name}'


class DataField(models.Model):
    FIELD_TYPES = [
        ('text', 'Text'),
        ('integer', 'Integer'),
        ('decimal', 'Decimal'),
        ('date', 'Date'),
        ('boolean', 'Boolean'),
        ('textarea', 'Long text'),
        ('derived', 'Derived / calculated'),
    ]

    # Keep experiment for backward compatibility with older code/admin queries.
    # The source of truth for new work is table.experiment.
    experiment = models.ForeignKey(
        Experiment,
        on_delete=models.CASCADE,
        related_name='fields',
        editable=False,
    )
    table = models.ForeignKey(
        ExperimentTable,
        on_delete=models.CASCADE,
        related_name='fields',
    )
    name = models.CharField(max_length=120)
    variable_name = models.SlugField(
        max_length=80,
        blank=True,
        help_text='Formula variable name, for example length, time_period, theta. Auto-filled from the field name if blank.',
    )
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES, default='text')
    calculation_formula = models.CharField(
        max_length=500,
        blank=True,
        help_text='Only for derived fields. Row-wise examples: length/time, 2*pi*r, sin(theta*pi/180).',
    )
    unit = models.CharField(max_length=40, blank=True)
    help_text = models.CharField(max_length=240, blank=True)
    required = models.BooleanField(default=True)
    min_value = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    max_value = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    order = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])

    class Meta:
        ordering = ['order', 'id']
        unique_together = [('table', 'name'), ('table', 'variable_name')]

    @property
    def is_derived(self):
        return self.field_type == 'derived'

    def _default_variable_name(self):
        base = slugify(self.name).replace('-', '_')[:70] or 'field'
        if base[0].isdigit():
            base = f'f_{base}'
        return base

    def clean(self):
        super().clean()
        if self.variable_name and '-' in self.variable_name:
            raise ValidationError({'variable_name': 'Use underscores instead of hyphens in formula variable names.'})
        if self.field_type == 'derived' and not self.calculation_formula.strip():
            raise ValidationError({'calculation_formula': 'Derived fields require a calculation formula.'})
        if self.field_type != 'derived' and self.calculation_formula.strip():
            raise ValidationError({'calculation_formula': 'Only derived fields should have formulas.'})
        if self.table_id:
            variable_name = self.variable_name or self._default_variable_name()
            duplicate = DataField.objects.filter(table=self.table, variable_name=variable_name).exclude(pk=self.pk)
            if duplicate.exists():
                raise ValidationError({'variable_name': 'This variable name is already used in this table.'})

    def save(self, *args, **kwargs):
        if self.table_id:
            self.experiment = self.table.experiment
        if not self.variable_name:
            self.variable_name = self._default_variable_name()
        if self.field_type == 'derived':
            self.required = False
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.table}: {self.name}'

class PlotConfig(models.Model):
    CHART_TYPES = [
        ("scatter", "Scatter plot"),
        ("line", "Line plot"),
        ("bar", "Bar chart"),
    ]

    table = models.ForeignKey(
        "ExperimentTable",
        on_delete=models.CASCADE,
        related_name="plot_configs",
    )
    title = models.CharField(max_length=200)
    chart_type = models.CharField(
        max_length=20,
        choices=CHART_TYPES,
        default="scatter",
    )

    x_field = models.ForeignKey(
        "DataField",
        on_delete=models.CASCADE,
        related_name="x_plot_configs",
    )
    y_field = models.ForeignKey(
        "DataField",
        on_delete=models.CASCADE,
        related_name="y_plot_configs",
    )

    x_axis_label = models.CharField(max_length=100, blank=True)
    y_axis_label = models.CharField(max_length=100, blank=True)

    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.title} ({self.table})"
    

class ResultField(models.Model):
    experiment = models.ForeignKey(
        Experiment,
        on_delete=models.CASCADE,
        related_name='result_fields',
    )
    name = models.CharField(max_length=160)
    variable_name = models.SlugField(
        max_length=80,
        blank=True,
        help_text='Result variable name. Later result formulas can use this name.',
    )
    calculation_formula = models.CharField(
        max_length=1000,
        help_text='Examples: mean(length.lmean), mean(time.t20)/20, 4*pi**2*L/(T**2).',
    )
    unit = models.CharField(max_length=40, blank=True)
    help_text = models.CharField(max_length=240, blank=True)
    order = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])

    class Meta:
        ordering = ['order', 'id']
        unique_together = [('experiment', 'variable_name')]

    def _default_variable_name(self):
        base = slugify(self.name).replace('-', '_')[:70] or 'result'
        if base[0].isdigit():
            base = f'r_{base}'
        return base

    def save(self, *args, **kwargs):
        if not self.variable_name:
            self.variable_name = self._default_variable_name()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.experiment}: {self.name}'


class Submission(models.Model):
    STATUS_CHOICES = [('submitted', 'Submitted'), ('approved', 'Approved'), ('needs_revision', 'Needs revision')]

    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE, related_name='submissions')
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    sample_id = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='submitted')
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_submissions',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.experiment} / {self.sample_id or self.pk}'


class ObservationRow(models.Model):
    """One serial-numbered row inside one experiment table."""
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='rows')
    table = models.ForeignKey(ExperimentTable, on_delete=models.CASCADE, related_name='rows')
    serial_number = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['table__order', 'serial_number', 'id']
        unique_together = [('submission', 'table', 'serial_number')]

    def __str__(self):
        return f'{self.submission} / {self.table.name} / row {self.serial_number}'


class FieldValue(models.Model):
    row = models.ForeignKey(ObservationRow, on_delete=models.CASCADE, related_name='values')
    field = models.ForeignKey(DataField, on_delete=models.CASCADE)
    value = models.TextField(blank=True)

    class Meta:
        unique_together = [('row', 'field')]

    def __str__(self):
        return f'Row {self.row.serial_number} / {self.field.name}: {self.value}'


class ResultValue(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='result_values')
    result_field = models.ForeignKey(ResultField, on_delete=models.CASCADE)
    value = models.TextField(blank=True)

    class Meta:
        unique_together = [('submission', 'result_field')]

    def __str__(self):
        return f'{self.submission} / {self.result_field.name}: {self.value}'


class Attachment(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='lab_uploads/%Y/%m/%d/')
    description = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)


class AuditLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100, blank=True)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
