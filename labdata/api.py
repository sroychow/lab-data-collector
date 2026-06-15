from django.contrib.auth import authenticate
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    DataField,
    Experiment,
    ExperimentTable,
    FieldValue,
    ObservationRow,
    PlotConfig,
    ResultField,
    ResultValue,
    Submission,
)
from .plotting import build_fit, build_plot_data
from .safe_formula import FormulaError, evaluate_formula, format_result


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    return Response(
        {
            "status": "ok",
            "service": "lab-data-collector-api",
        }
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def api_login(request):
    username = request.data.get("username", "")
    password = request.data.get("password", "")

    user = authenticate(request, username=username, password=password)

    if user is None:
        return Response(
            {
                "detail": "Invalid username or password.",
            },
            status=400,
        )

    token, _ = Token.objects.get_or_create(user=user)

    return Response(
        {
            "token": token.key,
            "user": {
                "id": user.id,
                "username": user.username,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
            },
        }
    )


def visible_submissions_for(user):
    qs = Submission.objects.all()

    if user.is_staff or user.is_superuser:
        return qs

    return qs.filter(submitted_by=user)


def build_complete_row_values(fields, input_values):
    complete_values = dict(input_values)
    variable_context = {}

    for field in fields:
        if field.is_derived:
            try:
                result = evaluate_formula(field.calculation_formula, variable_context)
                formatted = format_result(result)
            except FormulaError as exc:
                formatted = f"ERROR: {exc}"

            complete_values[field.id] = formatted
            variable_context[field.variable_name] = formatted

        elif field.field_type in ["integer", "decimal"]:
            variable_context[field.variable_name] = complete_values.get(field.id, "")

    return complete_values


def build_result_context(submission):
    context = {}
    rows = submission.rows.select_related("table").prefetch_related("values__field")

    for row in rows:
        table_key = row.table.variable_name
        table_context = context.setdefault(table_key, {})

        for value in row.values.all():
            field_key = value.field.variable_name
            table_context.setdefault(field_key, []).append(value.value)

    return context


def calculate_result_values(submission):
    context = build_result_context(submission)

    for result_field in submission.experiment.result_fields.all():
        try:
            value = evaluate_formula(result_field.calculation_formula, context)
            formatted = format_result(value)
            context[result_field.variable_name] = formatted
        except FormulaError as exc:
            formatted = f"ERROR: {exc}"

        ResultValue.objects.update_or_create(
            submission=submission,
            result_field=result_field,
            defaults={"value": formatted},
        )


class DataFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataField
        fields = [
            "id",
            "name",
            "variable_name",
            "field_type",
            "calculation_formula",
            "unit",
            "help_text",
            "required",
            "min_value",
            "max_value",
            "order",
        ]


class ExperimentTableSchemaSerializer(serializers.ModelSerializer):
    fields = DataFieldSerializer(many=True, read_only=True)

    class Meta:
        model = ExperimentTable
        fields = [
            "id",
            "name",
            "variable_name",
            "description",
            "order",
            "fields",
        ]


class ResultFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResultField
        fields = [
            "id",
            "name",
            "variable_name",
            "calculation_formula",
            "unit",
            "help_text",
            "order",
        ]


class PlotConfigSerializer(serializers.ModelSerializer):
    table = serializers.IntegerField(source="table_id")
    table_name = serializers.CharField(source="table.name", read_only=True)
    x_field = serializers.IntegerField(source="x_field_id")
    y_field = serializers.IntegerField(source="y_field_id")
    x_field_name = serializers.CharField(source="x_field.name", read_only=True)
    y_field_name = serializers.CharField(source="y_field.name", read_only=True)

    fit_type = serializers.SerializerMethodField()
    show_fit_equation = serializers.SerializerMethodField()

    class Meta:
        model = PlotConfig
        fields = [
            "id",
            "table",
            "table_name",
            "title",
            "chart_type",
            "x_field",
            "y_field",
            "x_field_name",
            "y_field_name",
            "x_axis_label",
            "y_axis_label",
            "fit_type",
            "show_fit_equation",
            "order",
            "is_active",
        ]

    def get_fit_type(self, obj):
        return getattr(obj, "fit_type", "none")

    def get_show_fit_equation(self, obj):
        return getattr(obj, "show_fit_equation", False)


class ExperimentListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experiment
        fields = [
            "id",
            "title",
            "slug",
            "course_or_project",
            "objective",
            "protocol_version",
            "status",
        ]


class ExperimentSchemaSerializer(serializers.ModelSerializer):
    tables = ExperimentTableSchemaSerializer(many=True, read_only=True)
    result_fields = ResultFieldSerializer(many=True, read_only=True)
    plot_configs = serializers.SerializerMethodField()

    class Meta:
        model = Experiment
        fields = [
            "id",
            "title",
            "slug",
            "course_or_project",
            "objective",
            "protocol_version",
            "status",
            "tables",
            "result_fields",
            "plot_configs",
        ]

    def get_plot_configs(self, obj):
        plot_configs = (
            PlotConfig.objects
            .filter(table__experiment=obj, is_active=True)
            .select_related("table", "x_field", "y_field")
            .order_by("order", "id")
        )
        return PlotConfigSerializer(plot_configs, many=True).data


class FieldValueSerializer(serializers.ModelSerializer):
    field_id = serializers.IntegerField(source="field.id", read_only=True)
    field_name = serializers.CharField(source="field.name", read_only=True)
    variable_name = serializers.CharField(source="field.variable_name", read_only=True)
    unit = serializers.CharField(source="field.unit", read_only=True)

    class Meta:
        model = FieldValue
        fields = [
            "field_id",
            "field_name",
            "variable_name",
            "unit",
            "value",
        ]


class ObservationRowSerializer(serializers.ModelSerializer):
    table_id = serializers.IntegerField(source="table.id", read_only=True)
    table_name = serializers.CharField(source="table.name", read_only=True)
    values = FieldValueSerializer(many=True, read_only=True)

    class Meta:
        model = ObservationRow
        fields = [
            "id",
            "table_id",
            "table_name",
            "serial_number",
            "values",
        ]


class ResultValueSerializer(serializers.ModelSerializer):
    result_field_id = serializers.IntegerField(source="result_field.id", read_only=True)
    name = serializers.CharField(source="result_field.name", read_only=True)
    variable_name = serializers.CharField(source="result_field.variable_name", read_only=True)
    unit = serializers.CharField(source="result_field.unit", read_only=True)
    formula = serializers.CharField(source="result_field.calculation_formula", read_only=True)

    class Meta:
        model = ResultValue
        fields = [
            "result_field_id",
            "name",
            "variable_name",
            "unit",
            "formula",
            "value",
        ]


class SubmissionListSerializer(serializers.ModelSerializer):
    experiment_title = serializers.CharField(source="experiment.title", read_only=True)
    experiment_slug = serializers.CharField(source="experiment.slug", read_only=True)
    submitted_by_username = serializers.CharField(source="submitted_by.username", read_only=True)

    class Meta:
        model = Submission
        fields = [
            "id",
            "experiment",
            "experiment_title",
            "experiment_slug",
            "sample_id",
            "notes",
            "status",
            "submitted_by_username",
            "created_at",
            "updated_at",
        ]


class SubmissionDetailSerializer(serializers.ModelSerializer):
    experiment_title = serializers.CharField(source="experiment.title", read_only=True)
    experiment_slug = serializers.CharField(source="experiment.slug", read_only=True)
    submitted_by_username = serializers.CharField(source="submitted_by.username", read_only=True)
    rows = ObservationRowSerializer(many=True, read_only=True)
    result_values = ResultValueSerializer(many=True, read_only=True)
    plot_configs = serializers.SerializerMethodField()

    class Meta:
        model = Submission
        fields = [
            "id",
            "experiment",
            "experiment_title",
            "experiment_slug",
            "sample_id",
            "notes",
            "status",
            "submitted_by_username",
            "created_at",
            "updated_at",
            "rows",
            "result_values",
            "plot_configs",
        ]

    def get_plot_configs(self, obj):
        plot_configs = (
            PlotConfig.objects
            .filter(table__experiment=obj.experiment, is_active=True)
            .select_related("table", "x_field", "y_field")
            .order_by("order", "id")
        )
        return PlotConfigSerializer(plot_configs, many=True).data


class ExperimentListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        experiments = (
            Experiment.objects
            .filter(status="active")
            .order_by("title")
        )
        return Response(ExperimentListSerializer(experiments, many=True).data)


class ExperimentSchemaAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        experiment = get_object_or_404(
            Experiment.objects
            .filter(status="active")
            .prefetch_related(
                "tables",
                "tables__fields",
                "result_fields",
            ),
            slug=slug,
        )

        return Response(ExperimentSchemaSerializer(experiment).data)


class ExperimentSubmissionCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, slug):
        experiment = get_object_or_404(Experiment, slug=slug, status="active")

        observation_rows = request.data.get("observation_rows", [])
        if not isinstance(observation_rows, list) or not observation_rows:
            return Response(
                {"detail": "At least one observation row is required."},
                status=400,
            )

        tables_by_id = {
            table.id: table
            for table in experiment.tables.prefetch_related("fields").all()
        }

        submission = Submission.objects.create(
            experiment=experiment,
            submitted_by=request.user,
            sample_id=request.data.get("sample_id", ""),
            notes=request.data.get("notes", ""),
        )

        errors = []

        for index, row_payload in enumerate(observation_rows, start=1):
            table_id = row_payload.get("table")
            serial_number = row_payload.get("serial_number", index)
            values_payload = row_payload.get("values", {})

            try:
                table_id = int(table_id)
            except (TypeError, ValueError):
                errors.append(f"Row {index}: invalid table id.")
                continue

            table = tables_by_id.get(table_id)
            if table is None:
                errors.append(f"Row {index}: table does not belong to this experiment.")
                continue

            if not isinstance(values_payload, dict):
                errors.append(f"Row {index}: values must be an object.")
                continue

            row = ObservationRow.objects.create(
                submission=submission,
                table=table,
                serial_number=serial_number,
            )

            fields = list(table.fields.all())
            numeric_input_values = {}

            for field in fields:
                raw_value = values_payload.get(str(field.id), values_payload.get(field.id, ""))

                if field.is_derived:
                    continue

                if field.required and str(raw_value).strip() == "":
                    errors.append(f"Row {index}: {field.name} is required.")

                numeric_input_values[field.id] = "" if raw_value is None else str(raw_value)

            complete_values = build_complete_row_values(fields, numeric_input_values)

            for field in fields:
                value = complete_values.get(field.id, "")
                FieldValue.objects.create(
                    row=row,
                    field=field,
                    value="" if value is None else str(value),
                )

        if errors:
            transaction.set_rollback(True)
            return Response(
                {
                    "detail": "Submission contains validation errors.",
                    "errors": errors,
                },
                status=400,
            )

        calculate_result_values(submission)

        submission = (
            Submission.objects
            .select_related("experiment", "submitted_by")
            .prefetch_related(
                "rows__table",
                "rows__values__field",
                "result_values__result_field",
            )
            .get(pk=submission.pk)
        )

        return Response(SubmissionDetailSerializer(submission).data, status=201)

'''
class SubmissionListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        submissions = (
            visible_submissions_for(request.user)
            .select_related("experiment", "submitted_by")
            .order_by("-created_at")
        )
        return Response(SubmissionListSerializer(submissions, many=True).data)
'''
class SubmissionListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        submissions = (
            visible_submissions_for(request.user)
            .select_related("experiment", "submitted_by")
            .order_by("-created_at")
        )
        experiment_slug = request.query_params.get("experiment")
        if experiment_slug:
            submissions = submissions.filter(experiment__slug=experiment_slug)

        return Response(SubmissionListSerializer(submissions, many=True).data)

class SubmissionDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        submission = get_object_or_404(
            visible_submissions_for(request.user)
            .select_related("experiment", "submitted_by")
            .prefetch_related(
                "rows__table",
                "rows__values__field",
                "result_values__result_field",
            ),
            pk=pk,
        )
        return Response(SubmissionDetailSerializer(submission).data)


class SubmissionPlotAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, plot_id):
        submission = get_object_or_404(
            visible_submissions_for(request.user).select_related("experiment"),
            pk=pk,
        )

        plot_config = get_object_or_404(
            PlotConfig.objects.select_related("table", "x_field", "y_field"),
            pk=plot_id,
            table__experiment=submission.experiment,
            is_active=True,
        )

        chart_data = build_plot_data(plot_config, submission)

        try:
            fit_result, fit_line = build_fit(plot_config, chart_data)
        except Exception:
            fit_result, fit_line = None, []

        return Response(
            {
                "submission": submission.id,
                "experiment": submission.experiment.title,
                "plot": PlotConfigSerializer(plot_config).data,
                "point_count": len(chart_data),
                "chart_data": chart_data,
                "fit_result": fit_result,
                "fit_line": fit_line,
            }
        )
