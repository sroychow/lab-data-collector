from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DataField, Experiment, ExperimentTable, PlotConfig, ResultField


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
