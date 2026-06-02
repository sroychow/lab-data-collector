from django.contrib import admin

from .models import (
    Attachment,
    AuditLog,
    DataField,
    Experiment,
    ExperimentTable,
    FieldValue,
    ObservationRow,
    ResultField,
    ResultValue,
    Submission,
    PlotConfig
)


class ExperimentTableInline(admin.TabularInline):
    model = ExperimentTable
    extra = 1
    fields = ('order', 'name', 'variable_name', 'description')
    show_change_link = True


class ResultFieldInline(admin.TabularInline):
    model = ResultField
    extra = 1
    fields = ('order', 'name', 'variable_name', 'calculation_formula', 'unit', 'help_text')


@admin.register(Experiment)
class ExperimentAdmin(admin.ModelAdmin):
    list_display = ('title', 'course_or_project', 'status', 'protocol_version', 'created_at')
    list_filter = ('status', 'course_or_project')
    search_fields = ('title', 'course_or_project')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ExperimentTableInline, ResultFieldInline]


class DataFieldInline(admin.TabularInline):
    model = DataField
    extra = 2
    fields = (
        'order', 'name', 'variable_name', 'field_type', 'calculation_formula',
        'unit', 'required', 'min_value', 'max_value', 'help_text'
    )


@admin.register(ExperimentTable)
class ExperimentTableAdmin(admin.ModelAdmin):
    list_display = ('experiment', 'order', 'name', 'variable_name')
    list_filter = ('experiment',)
    search_fields = ('name', 'variable_name', 'experiment__title')
    inlines = [DataFieldInline]


@admin.register(DataField)
class DataFieldAdmin(admin.ModelAdmin):
    list_display = ('experiment', 'table', 'order', 'name', 'variable_name', 'field_type', 'unit', 'required')
    list_filter = ('experiment', 'table', 'field_type')
    search_fields = ('name', 'variable_name', 'calculation_formula')
    fields = (
        'table', 'order', 'name', 'variable_name', 'field_type', 'calculation_formula',
        'unit', 'required', 'min_value', 'max_value', 'help_text'
    )


@admin.register(ResultField)
class ResultFieldAdmin(admin.ModelAdmin):
    list_display = ('experiment', 'order', 'name', 'variable_name', 'unit')
    list_filter = ('experiment',)
    search_fields = ('name', 'variable_name', 'calculation_formula')


class FieldValueInline(admin.TabularInline):
    model = FieldValue
    extra = 0


@admin.register(ObservationRow)
class ObservationRowAdmin(admin.ModelAdmin):
    list_display = ('submission', 'table', 'serial_number', 'created_at')
    list_filter = ('submission__experiment', 'table')
    inlines = [FieldValueInline]


class ObservationRowInline(admin.TabularInline):
    model = ObservationRow
    extra = 0
    show_change_link = True


class ResultValueInline(admin.TabularInline):
    model = ResultValue
    extra = 0


class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 0


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('experiment', 'sample_id', 'submitted_by', 'status', 'created_at')
    list_filter = ('status', 'experiment')
    search_fields = ('sample_id', 'notes')
    inlines = [ObservationRowInline, ResultValueInline, AttachmentInline]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'actor', 'action', 'model_name', 'object_id')
    list_filter = ('action', 'model_name')
    search_fields = ('details', 'object_id')
    readonly_fields = ('created_at',)

@admin.register(PlotConfig)
class PlotConfigAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "table",
        "chart_type",
        "x_field",
        "y_field",
        "is_active",
        "order",
    )
    list_filter = ("chart_type", "is_active", "table__experiment")
    search_fields = (
        "title",
        "table__name",
        "table__experiment__title",
        "x_field__name",
        "y_field__name",
    )

admin.site.register(Attachment)
