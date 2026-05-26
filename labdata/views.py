import csv
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from .forms import DynamicTableSubmissionForm, ExperimentForm
from .models import AuditLog, Experiment, FieldValue, ObservationRow, Submission, Attachment
from .safe_formula import FormulaError, evaluate_formula, format_result


def build_complete_row_values(fields, input_values):
    """Return {field_id: value} including server-calculated derived fields.

    Formulas may use variable_name values from numeric input fields and from
    earlier derived fields. If a derived field depends on another derived field,
    give the dependency a lower order value in Django admin.
    """
    complete_values = dict(input_values)
    variable_context = {}

    for field in fields:
        if field.is_derived:
            try:
                result = evaluate_formula(field.calculation_formula, variable_context)
                formatted = format_result(result)
            except FormulaError as exc:
                formatted = f'ERROR: {exc}'
            complete_values[field.id] = formatted
            variable_context[field.variable_name] = formatted
        elif field.field_type in ['integer', 'decimal']:
            variable_context[field.variable_name] = complete_values.get(field.id, '')

    return complete_values

@login_required
def dashboard(request):
    experiments = Experiment.objects.all()
    total_submissions = Submission.objects.count()
    recent = Submission.objects.select_related('experiment', 'submitted_by')[:8]
    return render(request, 'labdata/dashboard.html', {
        'experiments': experiments,
        'total_submissions': total_submissions,
        'recent': recent,
    })

@login_required
def experiment_list(request):
    experiments = Experiment.objects.all()
    return render(request, 'labdata/experiment_list.html', {'experiments': experiments})

@login_required
def experiment_create(request):
    if not request.user.is_staff:
        messages.error(request, 'Only staff users can create experiments. Use Django admin for field setup.')
        return redirect('experiment_list')
    form = ExperimentForm(request.POST or None)
    if form.is_valid():
        exp = form.save(commit=False)
        exp.created_by = request.user
        exp.save()
        AuditLog.objects.create(actor=request.user, action='created experiment', model_name='Experiment', object_id=str(exp.id))
        messages.success(request, 'Experiment created. Add data fields from the admin panel.')
        return redirect('experiment_detail', slug=exp.slug)
    return render(request, 'labdata/experiment_form.html', {'form': form})

@login_required
def experiment_detail(request, slug):
    experiment = get_object_or_404(Experiment, slug=slug)
    submissions = experiment.submissions.select_related('submitted_by')[:20]
    return render(request, 'labdata/experiment_detail.html', {'experiment': experiment, 'submissions': submissions})

@login_required
def submit_data(request, slug):
    experiment = get_object_or_404(Experiment, slug=slug, status='active')
    form = DynamicTableSubmissionForm(request.POST or None, request.FILES or None, experiment=experiment)
    fields = list(experiment.fields.all())
    if form.is_valid():
        submission = Submission.objects.create(
            experiment=experiment,
            submitted_by=request.user,
            sample_id=form.cleaned_data.get('sample_id', ''),
            notes=form.cleaned_data.get('notes', ''),
        )
        for row_data in form.cleaned_data['observation_rows']:
            row = ObservationRow.objects.create(
                submission=submission,
                serial_number=row_data['serial_number']
            )
            complete_values = build_complete_row_values(fields, row_data['values'])
            for field in fields:
                value = complete_values.get(field.id, '')
                FieldValue.objects.create(row=row, field=field, value='' if value is None else str(value))
        upload = form.cleaned_data.get('attachment')
        if upload:
            Attachment.objects.create(
                submission=submission,
                file=upload,
                description=form.cleaned_data.get('attachment_description', '')
            )
        AuditLog.objects.create(actor=request.user, action='submitted data', model_name='Submission', object_id=str(submission.id))
        messages.success(request, 'Data submitted and timestamped successfully. Derived fields were calculated automatically.')
        return redirect('experiment_detail', slug=experiment.slug)
    return render(request, 'labdata/submit_data.html', {'experiment': experiment, 'form': form, 'fields': fields, 'default_rows': range(1, 6)})

@login_required
def submission_detail(request, pk):
    submission = get_object_or_404(Submission.objects.select_related('experiment', 'submitted_by'), pk=pk)
    return render(request, 'labdata/submission_detail.html', {'submission': submission})

@login_required
def export_csv(request, slug):
    experiment = get_object_or_404(Experiment, slug=slug)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{experiment.slug}_submissions.csv"'
    writer = csv.writer(response)
    fields = list(experiment.fields.all())
    writer.writerow(['submission_id', 'created_at', 'submitted_by', 'sample_id', 'status', 'notes', 'serial_number'] + [f'{f.name} ({f.unit})' if f.unit else f.name for f in fields])
    for sub in experiment.submissions.select_related('submitted_by').prefetch_related('rows__values'):
        for row in sub.rows.all():
            value_map = {v.field_id: v.value for v in row.values.all()}
            writer.writerow([
                sub.id, sub.created_at.isoformat(), sub.submitted_by.username if sub.submitted_by else '',
                sub.sample_id, sub.status, sub.notes, row.serial_number,
                *[value_map.get(f.id, '') for f in fields]
            ])
    return response
