import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import DynamicTableSubmissionForm, ExperimentForm
from .models import (
    Attachment,
    AuditLog,
    Experiment,
    FieldValue,
    ObservationRow,
    ResultValue,
    Submission,
    PlotConfig
)
from .safe_formula import FormulaError, evaluate_formula, format_result
import json
from .plotting import build_plot_data

def build_complete_row_values(fields, input_values):
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


def build_result_context(submission):
    context = {}
    rows = submission.rows.select_related('table').prefetch_related('values__field')
    for row in rows:
        table_key = row.table.variable_name
        table_context = context.setdefault(table_key, {})
        for value in row.values.all():
            field_key = value.field.variable_name
            table_context.setdefault(field_key, []).append(value.value)
    return context


def calculate_result_values(submission):
    context = build_result_context(submission)
    results = []
    for result_field in submission.experiment.result_fields.all():
        try:
            value = evaluate_formula(result_field.calculation_formula, context)
            formatted = format_result(value)
            context[result_field.variable_name] = formatted
        except FormulaError as exc:
            formatted = f'ERROR: {exc}'
        ResultValue.objects.update_or_create(
            submission=submission,
            result_field=result_field,
            defaults={'value': formatted},
        )
        results.append((result_field, formatted))
    return results


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
        messages.error(request, 'Only staff users can create experiments. Use Django admin for table and field setup.')
        return redirect('experiment_list')
    form = ExperimentForm(request.POST or None)
    if form.is_valid():
        exp = form.save(commit=False)
        exp.created_by = request.user
        exp.save()
        AuditLog.objects.create(actor=request.user, action='created experiment', model_name='Experiment', object_id=str(exp.id))
        messages.success(request, 'Experiment created. Add tables, fields and final results from the admin panel.')
        return redirect('experiment_detail', slug=exp.slug)
    return render(request, 'labdata/experiment_form.html', {'form': form})


@login_required
def experiment_detail(request, slug=None, experiment_id=None):
    if slug is not None:
        experiment = get_object_or_404(Experiment, slug=slug)
    else:
        experiment = get_object_or_404(Experiment, id=experiment_id)

    submissions = (
        Submission.objects
        .filter(experiment=experiment)
        .select_related("submitted_by")
        .order_by("-created_at")
    )

    plot_configs = (
        PlotConfig.objects
        .filter(table__experiment=experiment, is_active=True)
        .select_related("table", "x_field", "y_field")
        .order_by("order", "id")
    )

    return render(request, "labdata/experiment_detail.html", {
        "experiment": experiment,
        "submissions": submissions,
        "plot_configs": plot_configs,
    })
'''
def experiment_detail(request, experiment_id):
    experiment = get_object_or_404(Experiment, id=experiment_id)

    submissions = (
        Submission.objects
        .filter(experiment=experiment)
        .select_related("submitted_by")
        .order_by("-submitted_at")
    )

    plot_configs = (
        PlotConfig.objects
        .filter(table__experiment=experiment, is_active=True)
        .select_related("table", "x_field", "y_field")
        .order_by("order", "id")
    )

    return render(request, "labdata/experiment_detail.html", {
        "experiment": experiment,
        "submissions": submissions,
        "plot_configs": plot_configs,
    })

'''
@login_required
def submission_detail(request, pk):
    submission = get_object_or_404(
        Submission.objects
        .select_related("experiment", "submitted_by")
        .prefetch_related("rows__values", "rows__values__field", "attachments"),
        pk=pk,
    )

    plot_configs = (
        PlotConfig.objects
        .filter(experiment=submission.experiment, is_active=True)
        .select_related("x_field", "y_field")
        .order_by("order", "id")
    )

    return render(request, "labdata/submission_detail.html", {
        "submission": submission,
        "plot_configs": plot_configs,
    })

@login_required
def submission_plot_detail(request, pk, plot_id):
    submission = get_object_or_404(
        Submission.objects.select_related("experiment", "submitted_by"),
        pk=pk,
    )

    plot_config = get_object_or_404(
        PlotConfig.objects.select_related("experiment", "x_field", "y_field"),
        pk=plot_id,
        experiment=submission.experiment,
        is_active=True,
    )

    chart_data = build_plot_data(plot_config, submission)

    return render(request, "labdata/plot_detail.html", {
        "submission": submission,
        "experiment": submission.experiment,
        "plot_config": plot_config,
        "chart_data_json": json.dumps(chart_data),
        "point_count": len(chart_data),
    })

@login_required
def plot_detail(request, plot_id, submission_id=None):
    plot_config = get_object_or_404(
        PlotConfig.objects.select_related(
            "table",
            "table__experiment",
            "x_field",
            "y_field",
        ),
        id=plot_id,
        is_active=True,
    )

    submission = None
    if submission_id is not None:
        submission = get_object_or_404(
            Submission,
            id=submission_id,
            experiment=plot_config.table.experiment,
        )

    chart_data = build_plot_data(plot_config, submission=submission)

    return render(request, "labdata/plot_detail.html", {
        "plot_config": plot_config,
        "experiment": plot_config.table.experiment,
        "submission": submission,
        "chart_data": chart_data,
    })



@login_required
def submit_data(request, slug):
    experiment = get_object_or_404(Experiment, slug=slug, status='active')
    form = DynamicTableSubmissionForm(request.POST or None, request.FILES or None, experiment=experiment)
    tables = list(experiment.tables.prefetch_related('fields'))

    if form.is_valid():
        submission = Submission.objects.create(
            experiment=experiment,
            submitted_by=request.user,
            sample_id=form.cleaned_data.get('sample_id', ''),
            notes=form.cleaned_data.get('notes', ''),
        )

        for row_data in form.cleaned_data['observation_rows']:
            table = row_data['table']
            row = ObservationRow.objects.create(
                submission=submission,
                table=table,
                serial_number=row_data['serial_number'],
            )
            fields = list(table.fields.all())
            complete_values = build_complete_row_values(fields, row_data['values'])
            for field in fields:
                value = complete_values.get(field.id, '')
                FieldValue.objects.create(row=row, field=field, value='' if value is None else str(value))

        calculate_result_values(submission)

        upload = form.cleaned_data.get('attachment')
        if upload:
            Attachment.objects.create(
                submission=submission,
                file=upload,
                description=form.cleaned_data.get('attachment_description', ''),
            )

        AuditLog.objects.create(actor=request.user, action='submitted data', model_name='Submission', object_id=str(submission.id))
        messages.success(request, 'Data submitted. Row-wise fields and final results were calculated automatically.')
        return redirect('experiment_detail', slug=experiment.slug)

    return render(request, 'labdata/submit_data.html', {
        'experiment': experiment,
        'form': form,
        'tables': tables,
        'default_rows': range(1, 6),
    })


@login_required
def submission_detail(request, pk):
    submission = get_object_or_404(
        Submission.objects.select_related('experiment', 'submitted_by').prefetch_related(
            'rows__table',
            'rows__values__field',
            'result_values__result_field',
            'attachments',
        ),
        pk=pk,
    )
    return render(request, 'labdata/submission_detail.html', {'submission': submission})


@login_required
def export_csv(request, slug):
    experiment = get_object_or_404(Experiment, slug=slug)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{experiment.slug}_submissions.csv"'
    writer = csv.writer(response)

    tables = list(experiment.tables.prefetch_related('fields'))
    result_fields = list(experiment.result_fields.all())

    header = ['submission_id', 'created_at', 'submitted_by', 'sample_id', 'status', 'notes', 'table', 'serial_number']
    all_field_headers = []
    for table in tables:
        for field in table.fields.all():
            label = f'{table.name}::{field.name}'
            if field.unit:
                label += f' ({field.unit})'
            all_field_headers.append((table.id, field.id, label))
    header.extend(label for _, _, label in all_field_headers)
    header.extend([f'Result::{rf.name} ({rf.unit})' if rf.unit else f'Result::{rf.name}' for rf in result_fields])
    writer.writerow(header)

    submissions = experiment.submissions.select_related('submitted_by').prefetch_related(
        'rows__table', 'rows__values__field', 'result_values__result_field'
    )

    for sub in submissions:
        result_map = {rv.result_field_id: rv.value for rv in sub.result_values.all()}
        for row in sub.rows.all():
            value_map = {v.field_id: v.value for v in row.values.all()}
            writer.writerow([
                sub.id,
                sub.created_at.isoformat(),
                sub.submitted_by.username if sub.submitted_by else '',
                sub.sample_id,
                sub.status,
                sub.notes,
                row.table.name,
                row.serial_number,
                *[value_map.get(field_id, '') if table_id == row.table_id else '' for table_id, field_id, _ in all_field_headers],
                *[result_map.get(rf.id, '') for rf in result_fields],
            ])
    return response

from .plotting import build_plot_data
@login_required
def plot_detail(request, plot_id):
    plot_config = get_object_or_404(
        PlotConfig.objects.select_related(
            "table",
            "table__experiment",
            "x_field",
            "y_field",
        ),
        id=plot_id,
        is_active=True,
    )

    chart_data = build_plot_data(plot_config)

    return render(request, "labdata/plot_detail.html", {
        "plot_config": plot_config,
        "experiment": plot_config.table.experiment,
        "chart_data": chart_data,
    })
