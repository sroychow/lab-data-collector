from decimal import Decimal, InvalidOperation
from django import forms
from .models import Experiment
from .safe_formula import FormulaError, evaluate_formula

class ExperimentForm(forms.ModelForm):
    class Meta:
        model = Experiment
        fields = ['title', 'course_or_project', 'objective', 'protocol_version', 'status']
        widgets = {
            'objective': forms.Textarea(attrs={'rows': 4}),
        }

class DynamicTableSubmissionForm(forms.Form):
    sample_id = forms.CharField(required=False, max_length=120, label='Sample / Run ID')
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}), label='Notes')
    attachment = forms.FileField(required=False, label='Upload raw data file')
    attachment_description = forms.CharField(required=False, max_length=200, label='File description')

    def __init__(self, *args, experiment=None, **kwargs):
        self.experiment = experiment
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        if not self.experiment:
            return cleaned

        rows = []
        row_indices = sorted({
            int(key.split('_')[1])
            for key in self.data.keys()
            if key.startswith('row_') and key.endswith('_serial') and key.split('_')[1].isdigit()
        })

        fields = list(self.experiment.fields.all())
        input_fields = [field for field in fields if not field.is_derived]
        derived_fields = [field for field in fields if field.is_derived]

        for index in row_indices:
            serial_raw = self.data.get(f'row_{index}_serial', '').strip()
            values = {}
            has_any_value = bool(serial_raw)

            for field in input_fields:
                key = f'row_{index}_field_{field.id}'
                raw = self.data.get(key, '')
                if isinstance(raw, str):
                    raw = raw.strip()
                    if field.field_type == 'decimal':
                        raw = raw.replace(',', '.')
                if raw not in ('', None):
                    has_any_value = True
                values[field.id] = raw

            # Completely blank rows are ignored.
            if not has_any_value:
                continue

            if not serial_raw:
                self.add_error(None, f'Row {index}: serial number is required.')
                continue
            try:
                serial = int(serial_raw)
                if serial <= 0:
                    raise ValueError
            except ValueError:
                self.add_error(None, f'Row {index}: serial number must be a positive integer.')
                continue

            for field in input_fields:
                value = values[field.id]
                if field.required and value in ('', None):
                    self.add_error(None, f'Row {serial}: {field.name} is required.')
                    continue
                if value in ('', None):
                    continue

                if field.field_type == 'integer':
                    try:
                        int(value)
                    except ValueError:
                        self.add_error(None, f'Row {serial}: {field.name} must be an integer.')
                elif field.field_type == 'decimal':
                    try:
                        Decimal(str(value))
                    except InvalidOperation:
                        self.add_error(None, f'Row {serial}: {field.name} must be a number.')

                if field.field_type in ['integer', 'decimal'] and value not in ('', None):
                    try:
                        numeric = Decimal(str(value))
                    except InvalidOperation:
                        continue
                    if field.min_value is not None and numeric < field.min_value:
                        self.add_error(None, f'Row {serial}: {field.name} must be at least {field.min_value}.')
                    if field.max_value is not None and numeric > field.max_value:
                        self.add_error(None, f'Row {serial}: {field.name} must be at most {field.max_value}.')

            # Validate that derived formulas can be evaluated for this row.
            # Actual storage happens in views.py after the Submission/ObservationRow exists.
            variable_context = {}
            for field in input_fields:
                if field.field_type in ['integer', 'decimal']:
                    variable_context[field.variable_name] = values.get(field.id)

            for field in derived_fields:
                try:
                    derived_value = evaluate_formula(field.calculation_formula, variable_context)
                    variable_context[field.variable_name] = derived_value
                except FormulaError as exc:
                    self.add_error(None, f'Row {serial}: could not calculate {field.name}: {exc}')

            rows.append({'serial_number': serial, 'values': values})

        if not rows:
            self.add_error(None, 'Please enter at least one observation row.')

        serials = [r['serial_number'] for r in rows]
        if len(serials) != len(set(serials)):
            self.add_error(None, 'Serial numbers must be unique within one submission.')

        cleaned['observation_rows'] = rows
        return cleaned
