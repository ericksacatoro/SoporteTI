from django.contrib import admin
from django.utils.html import format_html
from .models import Customer, SupportAgent, SLA, Equipment, Ticket, TicketHistory, TicketComment, MaintenanceEvent, AuditLog


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display  = ('full_name', 'user', 'company', 'department', 'phone', 'is_active', 'created_at')
    list_filter   = ('is_active', 'company')
    search_fields = ('full_name', 'user__username', 'user__email', 'company')
    list_editable = ('is_active',)


@admin.register(SupportAgent)
class SupportAgentAdmin(admin.ModelAdmin):
    list_display  = ('__str__', 'role', 'speciality', 'extension', 'is_available', 'created_at')
    list_filter   = ('role', 'speciality', 'is_available')
    search_fields = ('user__first_name', 'user__last_name', 'user__username')
    list_editable = ('is_available',)


@admin.register(SLA)
class SLAAdmin(admin.ModelAdmin):
    list_display = ('name', 'response_time_hours', 'resolution_time_hours', 'is_active', 'created_at')
    list_filter  = ('is_active',)
    search_fields= ('name',)


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display  = ('name', 'equipment_type', 'serial_number', 'status', 'owner', 'assigned_agent')
    list_filter   = ('equipment_type', 'status')
    search_fields = ('name', 'serial_number')


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display  = ('code', 'title', 'customer', 'agent', 'priority_badge', 'status_badge', 'category', 'is_deleted', 'created_at')
    list_filter   = ('status', 'priority', 'category', 'is_deleted')
    search_fields = ('code', 'title', 'customer__full_name')
    readonly_fields = ('code', 'created_at', 'updated_at')
    date_hierarchy  = 'created_at'

    def priority_badge(self, obj):
        colors = {'Baja': 'secondary', 'Media': 'primary', 'Alta': 'warning', 'Crítica': 'danger'}
        return format_html('<span class="badge bg-{}">{}</span>', colors.get(obj.priority, 'secondary'), obj.priority)
    priority_badge.short_description = 'Prioridad'

    def status_badge(self, obj):
        colors = {'Abierto': 'info', 'Asignado': 'primary', 'En proceso': 'warning',
                  'Pendiente': 'secondary', 'Resuelto': 'success', 'Validado': 'success', 'Cerrado': 'dark'}
        return format_html('<span class="badge bg-{}">{}</span>', colors.get(obj.status, 'secondary'), obj.status)
    status_badge.short_description = 'Estado'


@admin.register(TicketHistory)
class TicketHistoryAdmin(admin.ModelAdmin):
    list_display  = ('ticket', 'user', 'action', 'old_status', 'new_status', 'created_at')
    list_filter   = ('action',)
    search_fields = ('ticket__code',)
    readonly_fields = ('created_at',)


@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    list_display  = ('ticket', 'user', 'created_at')
    search_fields = ('ticket__code', 'user__username')


@admin.register(MaintenanceEvent)
class MaintenanceEventAdmin(admin.ModelAdmin):
    list_display = ('title', 'event_type', 'start_time', 'end_time', 'created_by')
    list_filter  = ('event_type',)
    search_fields= ('title',)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display  = ('created_at', 'user', 'action', 'entity', 'entity_id', 'ip_address')
    list_filter   = ('action', 'entity')
    search_fields = ('user__username', 'action', 'entity')
    readonly_fields = ('created_at',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
