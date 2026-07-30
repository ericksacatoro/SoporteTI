from django.urls import path
from . import views

app_name = 'helpdesk'

urlpatterns = [
    # ── Home ─────────────────────────────────────────────────────────
    path('', views.home_view, name='home'),

    # ── Dashboard (Admin y Agentes) ───────────────────────────────────
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # ── Tickets ──────────────────────────────────────────────────────
    path('tickets/',                    views.ticket_list_view,     name='ticket_list'),
    path('tickets/create/',             views.ticket_create_view,   name='ticket_create'),
    path('tickets/<int:pk>/',           views.ticket_detail_view,   name='ticket_detail'),
    path('tickets/<int:pk>/edit/',      views.ticket_edit_view,     name='ticket_edit'),
    path('tickets/<int:pk>/delete/',    views.ticket_delete_view,   name='ticket_delete'),
    path('tickets/<int:pk>/status/',    views.ticket_change_status,   name='ticket_status'),
    path('tickets/<int:pk>/assign/',    views.ticket_assign_agent,    name='ticket_assign'),
    path('tickets/update-priority/',    views.ticket_update_priority, name='ticket_update_priority'),

    # ── Calendario (Agentes y Admin) ──────────────────────────────────
    path('calendar/',                        views.calendar_view,         name='calendar'),
    path('calendar/events/',                 views.calendar_events_view,  name='calendar_events'),
    path('calendar/events/<int:pk>/update/', views.calendar_event_update, name='calendar_event_update'),
    path('calendar/events/<int:pk>/move/',   views.calendar_event_move,   name='calendar_event_move'),
    path('calendar/events/<int:pk>/delete/', views.calendar_event_delete, name='calendar_event_delete'),

    # ── Reportes (Agentes y Admin) ────────────────────────────────────
    path('reports/',   views.reports_view,   name='reports'),

    # ── Gestión: Clientes (Admin) ────────────────────────────────────
    path('gestion/usuarios/',                   views.user_list_view,   name='user_list'),
    path('gestion/usuarios/crear/',             views.user_create_view, name='user_create'),
    path('gestion/usuarios/<int:pk>/editar/',   views.user_edit_view,   name='user_edit'),
    path('gestion/usuarios/<int:pk>/eliminar/', views.user_delete_view, name='user_delete'),

    # ── Gestión: Agentes (Admin) ─────────────────────────────────────
    path('gestion/agentes/',                   views.agent_list_view,   name='agent_list'),
    path('gestion/agentes/crear/',             views.agent_create_view, name='agent_create'),
    path('gestion/agentes/<int:pk>/editar/',   views.agent_edit_view,   name='agent_edit'),
    path('gestion/agentes/<int:pk>/eliminar/', views.agent_delete_view, name='agent_delete'),

    # ── Gestión: SLA (Admin) ─────────────────────────────────────────
    path('gestion/slas/',                   views.sla_list_view,   name='sla_list'),
    path('gestion/slas/crear/',             views.sla_create_view, name='sla_create'),
    path('gestion/slas/<int:pk>/editar/',   views.sla_edit_view,   name='sla_edit'),
    path('gestion/slas/<int:pk>/eliminar/', views.sla_delete_view, name='sla_delete'),

    # ── Gestión: Equipos (Admin) ─────────────────────────────────────
    path('gestion/equipos/',                   views.equipment_list_view,   name='equipment_list'),
    path('gestion/equipos/crear/',             views.equipment_create_view, name='equipment_create'),
    path('gestion/equipos/<int:pk>/editar/',   views.equipment_edit_view,   name='equipment_edit'),
    path('gestion/equipos/<int:pk>/eliminar/', views.equipment_delete_view, name='equipment_delete'),

    # ── Auth ─────────────────────────────────────────────────────────
    path('logout/', views.logout_view, name='logout'),
]
