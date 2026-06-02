from decimal import Decimal, InvalidOperation

from django import forms

from .models import Experiment
from .safe_formula import FormulaError, evaluate_formula


class ExperimentForm(forms.ModelForm):
    class Meta:
        model = Experiment
        fields = ['title', 'course_or_project', 'objective', 'protocol_version', 'status']
        widgets = {'objective': forms.Textarea(attrs={'rows': 4})}


class DynamicTableSubmissionForm(forms.Form):
    sample_id = forms.CharField(required=False, max_length=120, label='Sample / Run ID')
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}), label='Notes')
    attachment = forms.FileField(required=False, label='Upload raw data file')
    attachment_description = forms.CharField(required=False, max_length=200, label='File description')

    def __init__(self, *args, experiment=None, **kwargs):
        self.experiment = experiment
        super().__init__(*args, **kwargs)

    def _validate_numeric_limits(self, serial, field, value):
        if field.field_type not in ['integer', 'decimal'] or value in ('', None):
            return
        try:
            numeric = Decimal(str(value).replace(',', '.'))
        except InvalidOperation:
            return
        if field.min_value is not None and numeric < field.min_value:
            self.add_error(None, f'Row {serial}: {field.name} must be at least {field.min_value}.')
        if field.max_value is not None and numeric > field.max_value:
            self.add_error(None, f'Row {serial}: {field.name} must be at most {field.max_value}.')

    def clean(self):
        cleaned = super().clean()
        if not self.experiment:
            return cleaned

        tables = list(self.experiment.tables.prefetch_related('fields'))
        all_rows = []

        for table in tables:
            fields = list(table.fields.all())
            input_fields = [field for field in fields if not field.is_derived]
            derived_fields = [field for field in fields if field.is_derived]

            prefix = f'table_{table.id}_row_'
            row_indices = sorted({
                int(key[len(prefix):].split('_')[0])
                for key in self.data.keys()
                if key.startswith(prefix)
                and key.endswith('_serial')
                and key[len(prefix):].split('_')[0].isdigit()
            })

            table_rows = []
            for index in row_indices:
                serial_raw = self.data.get(f'table_{table.id}_row_{index}_serial', '').strip()
                values = {}
                has_any_value = bool(serial_raw)

                for field in input_fields:
                    key = f'table_{table.id}_row_{index}_field_{field.id}'
                    raw = self.data.get(key, '')
                    if isinstance(raw, str):
                        raw = raw.strip()
                    if field.field_type == 'decimal':
                        raw = raw.replace(',', '.')
                    if raw not in ('', None):
                        has_any_value = True
                    values[field.id] = raw

                if not has_any_value:
                    continue

                if not serial_raw:
                    self.add_error(None, f'{table.name}, row {index}: serial number is required.')
                    continue

                try:
                    serial = int(serial_raw)
                    if serial <= 0:
                        raise ValueError
                except ValueError:
                    self.add_error(None, f'{table.name}, row {index}: serial number must be a positive integer.')
                    continue

                for field in input_fields:
                    value = values[field.id]
                    if field.required and value in ('', None):
                        self.add_error(None, f'{table.name}, row {serial}: {field.name} is required.')
                        continue
                    if value in ('', None):
                        continue
                    if field.field_type == 'integer':
                        try:
                            int(value)
                        except ValueError:
                            self.add_error(None, f'{table.name}, row {serial}: {field.name} must be an integer.')
                    elif field.field_type == 'decimal':
                        try:
                            Decimal(str(value))
                        except InvalidOperation:
                            self.add_error(None, f'{table.name}, row {serial}: {field.name} must be a number.')
                    self._validate_numeric_limits(serial, field, value)

                variable_context = {}
                for field in input_fields:
                    if field.field_type in ['integer', 'decimal']:
                        variable_context[field.variable_name] = values.get(field.id)

                for field in derived_fields:
                    try:
                        derived_value = evaluate_formula(field.calculation_formula, variable_context)
                        variable_context[field.variable_name] = derived_value
                    except FormulaError as exc:
                        self.add_error(None, f'{table.name}, row {serial}: could not calculate {field.name}: {exc}')

                table_rows.append({'table': table, 'serial_number': serial, 'values': values})

            if not table_rows:
                self.add_error(None, f'Please enter at least one observation row for table "{table.name}".')

            serials = [r['serial_number'] for r in table_rows]
            if len(serials) != len(set(serials)):
                self.add_error(None, f'Serial numbers must be unique inside table "{table.name}".')

            all_rows.extend(table_rows)

        cleaned['observation_rows'] = all_rows
        return cleaned
