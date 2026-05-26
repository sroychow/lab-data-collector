from django.contrib import admin
from .models import Attachment, AuditLog, DataField, Experiment, FieldValue, ObservationRow, Submission

class DataFieldInline(admin.TabularInline):
    model = DataField
    extra = 2
    fields = (
        'order', 'name', 'variable_name', 'field_type', 'calculation_formula',
        'unit', 'required', 'min_value', 'max_value', 'help_text'
    )

@admin.register(Experiment)
class ExperimentAdmin(admin.ModelAdmin):
    list_display = ('title', 'course_or_project', 'status', 'protocol_version', 'created_at')
    list_filter = ('status', 'course_or_project')
    search_fields = ('title', 'course_or_project')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [DataFieldInline]

class FieldValueInline(admin.TabularInline):
    model = FieldValue
    extra = 0

@admin.register(ObservationRow)
class ObservationRowAdmin(admin.ModelAdmin):
    list_display = ('submission', 'serial_number', 'created_at')
    list_filter = ('submission__experiment',)
    inlines = [FieldValueInline]

class ObservationRowInline(admin.TabularInline):
    model = ObservationRow
    extra = 0
    show_change_link = True

class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 0

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('experiment', 'sample_id', 'submitted_by', 'status', 'created_at')
    list_filter = ('status', 'experiment')
    search_fields = ('sample_id', 'notes')
    inlines = [ObservationRowInline, AttachmentInline]

@admin.register(DataField)
class DataFieldAdmin(admin.ModelAdmin):
    list_display = ('experiment', 'order', 'name', 'variable_name', 'field_type', 'unit', 'required')
    list_filter = ('experiment', 'field_type')
    search_fields = ('name', 'variable_name', 'calculation_formula')
    fields = (
        'experiment', 'order', 'name', 'variable_name', 'field_type', 'calculation_formula',
        'unit', 'required', 'min_value', 'max_value', 'help_text'
    )

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'actor', 'action', 'model_name', 'object_id')
    list_filter = ('action', 'model_name')
    search_fields = ('details', 'object_id')
    readonly_fields = ('created_at',)

admin.site.register(Attachment)
