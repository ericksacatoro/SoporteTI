from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Count, F, Q
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth import logout
import json
import re

from .models import (
    Customer, SupportAgent, SLA, Equipment, Ticket,
    TicketHistory, TicketComment, MaintenanceEvent, AuditLog
)

# ─── Helpers de permisos ─────────────────────────────────────────────────────
# Tres roles: Admin (superuser) | Agente (tiene SupportAgent) | Cliente (tiene Customer)

def is_admin(user):
    return user.is_authenticated and user.is_superuser

def is_agent(user):
    return user.is_authenticated and hasattr(user, 'support_agent')

def is_customer(user):
    return user.is_authenticated and hasattr(user, 'customer')

def is_supervisor(user):
    return is_agent(user) and user.support_agent.role == 'Supervisor'

def is_supervisor_or_admin(user):
    return is_admin(user) or is_supervisor(user)

def is_agent_or_higher(user):
    return is_admin(user) or is_agent(user)

def get_client_ip(request):
    x = request.META.get('HTTP_X_FORWARDED_FOR')
    return x.split(',')[0] if x else request.META.get('REMOTE_ADDR')

def audit(request, action, entity, entity_id=None, detail=''):
    AuditLog.objects.create(
        user=request.user if request.user.is_authenticated else None,
        action=action, entity=entity, entity_id=entity_id,
        detail=detail, ip_address=get_client_ip(request)
    )

def add_history(ticket, user, action, old_val='', new_val='', old_st='', new_st='', comment=''):
    TicketHistory.objects.create(
        ticket=ticket, user=user, action=action,
        old_value=old_val, new_value=new_val,
        old_status=old_st, new_status=new_st,
        comment=comment
    )


# ─── Auth ────────────────────────────────────────────────────────────────────

@require_http_methods(["GET", "POST"])
def logout_view(request):
    logout(request)
    return redirect('/login/')

def home_view(request):
    if request.user.is_authenticated:
        if is_agent_or_higher(request.user):
            return redirect('/dashboard/')
        return redirect('/tickets/')
    return redirect('/login/')


# ─── Dashboard (Admin y Agentes) ─────────────────────────────────────────────

@login_required
def dashboard_view(request):
    if not is_agent_or_higher(request.user):
        return redirect('/tickets/')

    qs = Ticket.objects.filter(is_deleted=False)

    # Agente no supervisor: solo sus tickets
    if is_agent(request.user) and not is_supervisor_or_admin(request.user):
        qs = qs.filter(agent=request.user.support_agent)

    now        = timezone.now()
    total      = qs.count()
    open_t     = qs.filter(status='Abierto').count()
    in_process = qs.filter(status='En proceso').count()
    resolved   = qs.filter(status='Resuelto').count()
    pending    = qs.filter(status='Pendiente').count()
    overdue    = qs.filter(due_date__lt=now).exclude(
                    status__in=['Resuelto', 'Cerrado', 'Validado']).count()

    # ── SLA: desglose real ────────────────────────────────────────────────
    # Tickets con SLA asignado (tienen due_date)
    qs_sla = qs.filter(due_date__isnull=False)
    sla_total     = qs_sla.count()
    # Cumplido: resuelto antes o en la fecha límite
    sla_cumplido  = qs_sla.filter(
        resolved_at__isnull=False, resolved_at__lte=F('due_date')).count()
    # Incumplido: resuelto tarde O aún abierto pero ya vencido
    sla_incumplido = qs_sla.filter(
        resolved_at__isnull=False, resolved_at__gt=F('due_date')).count()
    sla_incumplido += qs_sla.filter(
        resolved_at__isnull=True, due_date__lt=now).exclude(
        status__in=['Cerrado', 'Validado']).count()
    # Pendiente: aún dentro del plazo o sin resolver
    sla_pendiente = max(sla_total - sla_cumplido - sla_incumplido, 0)
    sla_compliance = round((sla_cumplido / sla_total) * 100, 1) if sla_total else 0

    # ── MTTR global ───────────────────────────────────────────────────────
    resolved_list = list(qs.filter(resolved_at__isnull=False).values('resolved_at', 'created_at'))
    mttr_hours = round(
        sum((t['resolved_at'] - t['created_at']).total_seconds() for t in resolved_list)
        / len(resolved_list) / 3600, 1) if resolved_list else 0

    # ── MTTR por prioridad ────────────────────────────────────────────────
    priorities = ['Crítica', 'Alta', 'Media', 'Baja']
    mttr_by_priority = []
    for p in priorities:
        lst = list(qs.filter(priority=p, resolved_at__isnull=False)
                     .values('resolved_at', 'created_at'))
        mttr_h = round(
            sum((t['resolved_at'] - t['created_at']).total_seconds() for t in lst)
            / len(lst) / 3600, 1) if lst else 0
        mttr_by_priority.append({'priority': p, 'mttr_hours': mttr_h, 'count': len(lst)})

    six_months_ago = now - timezone.timedelta(days=180)
    monthly = list(
        qs.filter(created_at__gte=six_months_ago)
          .annotate(month=TruncMonth('created_at'))
          .values('month').annotate(total=Count('id')).order_by('month')
    )

    return render(request, 'dashboard.html', {
        'total': total, 'open_t': open_t, 'in_process': in_process,
        'resolved': resolved, 'pending': pending, 'overdue': overdue,
        'sla_compliance':  sla_compliance,
        'sla_cumplido':    sla_cumplido,
        'sla_incumplido':  sla_incumplido,
        'sla_pendiente':   sla_pendiente,
        'sla_total':       sla_total,
        'mttr_hours':      mttr_hours,
        'mttr_by_priority': json.dumps(mttr_by_priority, default=str),
        'monthly':          json.dumps(monthly, default=str),
    })


# ─── Gestión de Clientes (solo Admin) ────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def user_list_view(request):
    customers = Customer.objects.select_related('user').order_by('full_name')
    return render(request, 'admin_users.html', {'customers': customers})


@login_required
@user_passes_test(is_admin)
def user_create_view(request):
    if request.method == 'POST':
        username   = request.POST.get('username', '').strip()
        password   = request.POST.get('password', '').strip()
        email      = request.POST.get('email', '').strip()
        full_name  = request.POST.get('full_name', '').strip()
        phone      = request.POST.get('phone', '').strip()
        company    = request.POST.get('company', '').strip()
        department = request.POST.get('department', '').strip()
        position   = request.POST.get('position', '').strip()

        errors = []
        if not all([username, password, email, full_name]):
            errors.append('Usuario, contraseña, email y nombre completo son obligatorios.')
        if full_name and not re.match(r'^[A-Za-záéíóúÁÉÍÓÚñÑüÜ\s\-]+$', full_name):
            errors.append('El nombre completo solo puede contener letras y espacios.')
        if phone and not re.match(r'^[\d\+\-\s\(\)]{7,20}$', phone):
            errors.append('Teléfono inválido.')
        if username and User.objects.filter(username=username).exists():
            errors.append('El nombre de usuario ya existe.')
        if email and User.objects.filter(email=email).exists():
            errors.append('El correo ya está registrado.')

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'admin_user_form.html', {
                'title': 'Crear Cliente', 'customer': None, 'form_data': request.POST})

        parts = full_name.split(' ', 1)
        u = User.objects.create_user(
            username=username, password=password, email=email,
            first_name=parts[0], last_name=parts[1] if len(parts) > 1 else '')
        Customer.objects.create(
            user=u, full_name=full_name, phone=phone,
            company=company, department=department, position=position)
        audit(request, 'CREATE', 'Customer', u.id, f'Cliente {username} creado')
        messages.success(request, f'Cliente "{full_name}" creado correctamente.')
        return redirect('/gestion/usuarios/')

    return render(request, 'admin_user_form.html', {'title': 'Crear Cliente', 'customer': None})


@login_required
@user_passes_test(is_admin)
def user_edit_view(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        username   = request.POST.get('username', '').strip()
        email      = request.POST.get('email', '').strip()
        full_name  = request.POST.get('full_name', '').strip()
        phone      = request.POST.get('phone', '').strip()
        company    = request.POST.get('company', '').strip()
        department = request.POST.get('department', '').strip()
        position   = request.POST.get('position', '').strip()
        is_active  = request.POST.get('is_active') == 'on'
        new_pass   = request.POST.get('new_password', '').strip()

        errors = []
        if not all([username, email, full_name]):
            errors.append('Usuario, email y nombre completo son obligatorios.')
        if full_name and not re.match(r'^[A-Za-záéíóúÁÉÍÓÚñÑüÜ\s\-]+$', full_name):
            errors.append('El nombre completo solo puede contener letras y espacios.')
        if phone and not re.match(r'^[\d\+\-\s\(\)]{7,20}$', phone):
            errors.append('Teléfono inválido.')
        if User.objects.filter(username=username).exclude(pk=customer.user.pk).exists():
            errors.append('Ese nombre de usuario ya está en uso.')
        if User.objects.filter(email=email).exclude(pk=customer.user.pk).exists():
            errors.append('Ese correo ya está registrado por otro usuario.')

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'admin_user_form.html', {
                'title': 'Editar Cliente', 'customer': customer, 'form_data': request.POST})

        u = customer.user
        parts = full_name.split(' ', 1)
        u.username   = username
        u.email      = email
        u.first_name = parts[0]
        u.last_name  = parts[1] if len(parts) > 1 else ''
        u.is_active  = is_active
        if new_pass:
            u.set_password(new_pass)
        u.save()

        customer.full_name  = full_name
        customer.phone      = phone
        customer.company    = company
        customer.department = department
        customer.position   = position
        customer.is_active  = is_active
        customer.save()

        audit(request, 'UPDATE', 'Customer', pk, f'Cliente {username} editado')
        messages.success(request, 'Cliente actualizado correctamente.')
        return redirect('/gestion/usuarios/')

    return render(request, 'admin_user_form.html', {'title': 'Editar Cliente', 'customer': customer})


@login_required
@user_passes_test(is_admin)
def user_delete_view(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        customer.is_active = False
        customer.user.is_active = False
        customer.user.save()
        customer.save()
        audit(request, 'DELETE', 'Customer', pk, f'Cliente {customer.user.username} desactivado')
        messages.success(request, 'Cliente desactivado.')
        return redirect('/gestion/usuarios/')
    return render(request, 'confirm_delete.html', {'object': customer, 'back_url': '/gestion/usuarios/'})


# ─── Gestión de Agentes (solo Admin) ─────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def agent_list_view(request):
    agents = SupportAgent.objects.select_related('user').all()
    return render(request, 'admin_agents.html', {'agents': agents})


@login_required
@user_passes_test(is_admin)
def agent_create_view(request):
    if request.method == 'POST':
        username     = request.POST.get('username', '').strip()
        password     = request.POST.get('password', '').strip()
        email        = request.POST.get('email', '').strip()
        first_name   = request.POST.get('first_name', '').strip()
        last_name    = request.POST.get('last_name', '').strip()
        role         = request.POST.get('role', 'Analista')
        speciality   = request.POST.get('speciality', 'Otros')
        extension    = request.POST.get('extension', '').strip()
        is_available = request.POST.get('is_available') == 'on'

        errors = []
        if not all([username, password, email, first_name, last_name]):
            errors.append('Todos los campos obligatorios deben completarse.')
        if first_name and not re.match(r'^[A-Za-záéíóúÁÉÍÓÚñÑüÜ\s\-]+$', first_name):
            errors.append('El nombre solo puede contener letras.')
        if last_name and not re.match(r'^[A-Za-záéíóúÁÉÍÓÚñÑüÜ\s\-]+$', last_name):
            errors.append('El apellido solo puede contener letras.')
        if username and User.objects.filter(username=username).exists():
            errors.append('El nombre de usuario ya existe.')

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'admin_agent_form.html', {
                'title': 'Crear Agente', 'agent': None, 'form_data': request.POST})

        u = User.objects.create_user(
            username=username, password=password, email=email,
            first_name=first_name, last_name=last_name)
        SupportAgent.objects.create(
            user=u, role=role, speciality=speciality,
            extension=extension, is_available=is_available)
        audit(request, 'CREATE', 'SupportAgent', u.id, f'Agente {username} creado')
        messages.success(request, f'Agente {first_name} {last_name} creado.')
        return redirect('/gestion/agentes/')

    return render(request, 'admin_agent_form.html', {'title': 'Crear Agente', 'agent': None})


@login_required
@user_passes_test(is_admin)
def agent_edit_view(request, pk):
    agent = get_object_or_404(SupportAgent, pk=pk)
    if request.method == 'POST':
        username     = request.POST.get('username', '').strip()
        email        = request.POST.get('email', '').strip()
        first_name   = request.POST.get('first_name', '').strip()
        last_name    = request.POST.get('last_name', '').strip()
        role         = request.POST.get('role', agent.role)
        speciality   = request.POST.get('speciality', agent.speciality)
        extension    = request.POST.get('extension', '').strip()
        is_available = request.POST.get('is_available') == 'on'
        new_pass     = request.POST.get('new_password', '').strip()

        errors = []
        if not all([username, email, first_name, last_name]):
            errors.append('Usuario, email, nombre y apellido son obligatorios.')
        if first_name and not re.match(r'^[A-Za-záéíóúÁÉÍÓÚñÑüÜ\s\-]+$', first_name):
            errors.append('El nombre solo puede contener letras.')
        if last_name and not re.match(r'^[A-Za-záéíóúÁÉÍÓÚñÑüÜ\s\-]+$', last_name):
            errors.append('El apellido solo puede contener letras.')
        if User.objects.filter(username=username).exclude(pk=agent.user.pk).exists():
            errors.append('Ese nombre de usuario ya está en uso.')

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'admin_agent_form.html', {
                'title': 'Editar Agente', 'agent': agent, 'form_data': request.POST})

        u = agent.user
        u.username   = username
        u.email      = email
        u.first_name = first_name
        u.last_name  = last_name
        if new_pass:
            u.set_password(new_pass)
        u.save()

        agent.role         = role
        agent.speciality   = speciality
        agent.extension    = extension
        agent.is_available = is_available
        agent.save()

        audit(request, 'UPDATE', 'SupportAgent', pk, f'Agente {username} editado')
        messages.success(request, 'Agente actualizado correctamente.')
        return redirect('/gestion/agentes/')

    return render(request, 'admin_agent_form.html', {'title': 'Editar Agente', 'agent': agent})


@login_required
@user_passes_test(is_admin)
def agent_delete_view(request, pk):
    agent = get_object_or_404(SupportAgent, pk=pk)
    if Ticket.objects.filter(agent=agent, is_deleted=False).exists():
        messages.error(request, 'No se puede eliminar: el agente tiene tickets asignados.')
        return redirect('/gestion/agentes/')
    if request.method == 'POST':
        agent.user.delete()
        audit(request, 'DELETE', 'SupportAgent', pk, 'Agente eliminado')
        messages.success(request, 'Agente eliminado.')
        return redirect('/gestion/agentes/')
    return render(request, 'confirm_delete.html', {'object': agent, 'back_url': '/gestion/agentes/'})


# ─── Gestión de SLA (Admin) ───────────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def sla_list_view(request):
    return render(request, 'admin_slas.html', {'slas': SLA.objects.all()})


@login_required
@user_passes_test(is_admin)
def sla_create_view(request):
    if request.method == 'POST':
        name    = request.POST.get('name', '').strip()
        resp_h  = request.POST.get('response_time_hours', '')
        resol_h = request.POST.get('resolution_time_hours', '')
        desc    = request.POST.get('description', '').strip()
        active  = request.POST.get('is_active') == 'on'

        if not all([name, resp_h, resol_h]):
            messages.error(request, 'Nombre, tiempo de respuesta y resolución son obligatorios.')
            return render(request, 'admin_sla_form.html', {'title': 'Crear SLA'})
        if SLA.objects.filter(name=name).exists():
            messages.error(request, 'Ya existe un SLA con ese nombre.')
            return render(request, 'admin_sla_form.html', {'title': 'Crear SLA'})

        sla = SLA.objects.create(
            name=name, response_time_hours=int(resp_h),
            resolution_time_hours=int(resol_h), description=desc, is_active=active)
        audit(request, 'CREATE', 'SLA', sla.id, f'SLA {name} creado')
        messages.success(request, f'SLA "{name}" creado.')
        return redirect('/gestion/slas/')
    return render(request, 'admin_sla_form.html', {'title': 'Crear SLA'})


@login_required
@user_passes_test(is_admin)
def sla_edit_view(request, pk):
    sla = get_object_or_404(SLA, pk=pk)
    if request.method == 'POST':
        name    = request.POST.get('name', '').strip()
        resp_h  = request.POST.get('response_time_hours', '')
        resol_h = request.POST.get('resolution_time_hours', '')
        desc    = request.POST.get('description', '').strip()
        active  = request.POST.get('is_active') == 'on'

        if not all([name, resp_h, resol_h]):
            messages.error(request, 'Nombre, tiempo de respuesta y resolución son obligatorios.')
            return render(request, 'admin_sla_form.html', {'title': 'Editar SLA', 'sla': sla})
        if SLA.objects.filter(name=name).exclude(pk=pk).exists():
            messages.error(request, 'Ya existe otro SLA con ese nombre.')
            return render(request, 'admin_sla_form.html', {'title': 'Editar SLA', 'sla': sla})

        sla.name = name
        sla.response_time_hours   = int(resp_h)
        sla.resolution_time_hours = int(resol_h)
        sla.description = desc
        sla.is_active   = active
        sla.save()
        audit(request, 'UPDATE', 'SLA', pk, f'SLA {name} editado')
        messages.success(request, 'SLA actualizado.')
        return redirect('/gestion/slas/')
    return render(request, 'admin_sla_form.html', {'title': 'Editar SLA', 'sla': sla})


@login_required
@user_passes_test(is_admin)
def sla_delete_view(request, pk):
    sla = get_object_or_404(SLA, pk=pk)
    if Ticket.objects.filter(sla=sla, is_deleted=False).exists():
        messages.error(request, 'No se puede eliminar: hay tickets activos con este SLA.')
        return redirect('/gestion/slas/')
    if request.method == 'POST':
        sla.delete()
        audit(request, 'DELETE', 'SLA', pk, f'SLA {sla.name} eliminado')
        messages.success(request, 'SLA eliminado.')
        return redirect('/gestion/slas/')
    return render(request, 'confirm_delete.html', {'object': sla, 'back_url': '/gestion/slas/'})


# ─── Gestión de Equipos (Admin) ───────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def equipment_list_view(request):
    equipments = Equipment.objects.select_related('owner', 'assigned_agent').all()
    return render(request, 'admin_equipments.html', {'equipments': equipments})


@login_required
@user_passes_test(is_admin)
def equipment_create_view(request):
    if request.method == 'POST':
        name          = request.POST.get('name', '').strip()
        eq_type       = request.POST.get('equipment_type', 'Otro')
        serial        = request.POST.get('serial_number', '').strip()
        status        = request.POST.get('status', 'Operativo')
        owner_id      = request.POST.get('owner')
        agent_id      = request.POST.get('assigned_agent')
        purchase_date = request.POST.get('purchase_date') or None
        description   = request.POST.get('description', '').strip()

        errors = []
        if not all([name, serial, eq_type]):
            errors.append('Nombre, número serial y tipo son obligatorios.')
        if serial and not re.match(r'^[A-Za-z0-9\-\_\.]{3,50}$', serial):
            errors.append('El serial solo puede contener letras, números, guiones y puntos (3-50 caracteres).')
        if serial and Equipment.objects.filter(serial_number=serial).exists():
            errors.append('El número serial ya existe.')

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'admin_equipment_form.html', {
                'title': 'Crear Equipo', 'form_data': request.POST,
                'customers': Customer.objects.filter(is_active=True),
                'agents': SupportAgent.objects.filter(is_available=True)})

        eq = Equipment.objects.create(
            name=name, equipment_type=eq_type, serial_number=serial, status=status,
            owner=Customer.objects.get(pk=owner_id) if owner_id else None,
            assigned_agent=SupportAgent.objects.get(pk=agent_id) if agent_id else None,
            purchase_date=purchase_date, description=description)
        audit(request, 'CREATE', 'Equipment', eq.id, f'Equipo {name} creado')
        messages.success(request, f'Equipo "{name}" creado.')
        return redirect('/gestion/equipos/')

    return render(request, 'admin_equipment_form.html', {
        'title': 'Crear Equipo',
        'customers': Customer.objects.filter(is_active=True),
        'agents': SupportAgent.objects.filter(is_available=True)})


@login_required
@user_passes_test(is_admin)
def equipment_edit_view(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)
    if request.method == 'POST':
        name          = request.POST.get('name', '').strip()
        eq_type       = request.POST.get('equipment_type', equipment.equipment_type)
        serial        = request.POST.get('serial_number', '').strip()
        status        = request.POST.get('status', equipment.status)
        owner_id      = request.POST.get('owner')
        agent_id      = request.POST.get('assigned_agent')
        purchase_date = request.POST.get('purchase_date') or None
        description   = request.POST.get('description', '').strip()

        errors = []
        if not all([name, serial, eq_type]):
            errors.append('Nombre, número serial y tipo son obligatorios.')
        if serial and not re.match(r'^[A-Za-z0-9\-\_\.]{3,50}$', serial):
            errors.append('El serial solo puede contener letras, números, guiones y puntos (3-50 caracteres).')
        if serial and Equipment.objects.filter(serial_number=serial).exclude(pk=pk).exists():
            errors.append('Ese número serial ya está en uso.')

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'admin_equipment_form.html', {
                'title': 'Editar Equipo', 'equipment': equipment, 'form_data': request.POST,
                'customers': Customer.objects.filter(is_active=True),
                'agents': SupportAgent.objects.filter(is_available=True)})

        equipment.name           = name
        equipment.equipment_type = eq_type
        equipment.serial_number  = serial
        equipment.status         = status
        equipment.owner          = Customer.objects.get(pk=owner_id) if owner_id else None
        equipment.assigned_agent = SupportAgent.objects.get(pk=agent_id) if agent_id else None
        equipment.purchase_date  = purchase_date
        equipment.description    = description
        equipment.save()
        audit(request, 'UPDATE', 'Equipment', pk, f'Equipo {name} editado')
        messages.success(request, 'Equipo actualizado.')
        return redirect('/gestion/equipos/')

    return render(request, 'admin_equipment_form.html', {
        'title': 'Editar Equipo', 'equipment': equipment,
        'customers': Customer.objects.filter(is_active=True),
        'agents': SupportAgent.objects.filter(is_available=True)})


@login_required
@user_passes_test(is_admin)
def equipment_delete_view(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)
    if Ticket.objects.filter(equipment=equipment, is_deleted=False).exists():
        messages.error(request, 'No se puede eliminar: el equipo tiene tickets asociados.')
        return redirect('/gestion/equipos/')
    if request.method == 'POST':
        equipment.delete()
        audit(request, 'DELETE', 'Equipment', pk, f'Equipo {equipment.name} eliminado')
        messages.success(request, 'Equipo eliminado.')
        return redirect('/gestion/equipos/')
    return render(request, 'confirm_delete.html', {'object': equipment, 'back_url': '/gestion/equipos/'})


# ─── Tickets ──────────────────────────────────────────────────────────────────

@login_required
def ticket_list_view(request):
    user = request.user
    qs = Ticket.objects.filter(is_deleted=False).select_related('customer', 'agent', 'sla')

    if is_admin(user) or is_supervisor(user):
        pass  # ven todos
    elif is_agent(user):
        qs = qs.filter(agent=user.support_agent)
    elif is_customer(user):
        qs = qs.filter(customer=user.customer)
    else:
        qs = Ticket.objects.none()

    for field in ['status', 'priority', 'category']:
        val = request.GET.get(field)
        if val:
            qs = qs.filter(**{field: val})
    q = request.GET.get('q')
    if q:
        qs = qs.filter(Q(code__icontains=q) | Q(title__icontains=q) | Q(description__icontains=q))

    return render(request, 'tickets_list.html', {
        'tickets': qs.order_by('-created_at'),
        'status_choices':   Ticket.STATUS_CHOICES,
        'priority_choices': Ticket.PRIORITY_CHOICES,
        'category_choices': Ticket.CATEGORY_CHOICES,
        'priority_order':   ['Crítica', 'Alta', 'Media', 'Baja'],
        'filters': {
            'status':   request.GET.get('status', ''),
            'priority': request.GET.get('priority', ''),
            'category': request.GET.get('category', ''),
            'q':        request.GET.get('q', ''),
        },
    })


@login_required
def ticket_create_view(request):
    user = request.user

    if request.method == 'POST':
        title        = request.POST.get('title', '').strip()
        description  = request.POST.get('description', '').strip()
        category     = request.POST.get('category', 'Otros')
        priority     = request.POST.get('priority', 'Media')
        sla_id       = request.POST.get('sla')
        equipment_id = request.POST.get('equipment')
        customer_id  = request.POST.get('customer')
        agent_id     = request.POST.get('agent')
        attachment   = request.FILES.get('attachment')

        errors = []
        if not title or len(title) < 5:
            errors.append('El título es obligatorio y debe tener al menos 5 caracteres.')
        if not description or len(description) < 10:
            errors.append('La descripción es obligatoria y debe tener al menos 10 caracteres.')
        if errors:
            for e in errors:
                messages.error(request, e)
            return _ticket_form_ctx(request, 'Nuevo Ticket')

        # Determinar cliente y agente según rol
        if is_customer(user):
            customer = user.customer
            priority = 'Media'
            sla_id   = None
            agent_id = None
        elif is_agent_or_higher(user):
            if not customer_id:
                messages.error(request, 'Debes seleccionar un cliente.')
                return _ticket_form_ctx(request, 'Nuevo Ticket')
            customer = get_object_or_404(Customer, pk=customer_id, is_active=True)
            
            # Si es agente y no especificó agente, auto-asignarse
            if is_agent(user) and not agent_id:
                agent_id = user.support_agent.pk
        else:
            return redirect('/tickets/')

        ticket = Ticket.objects.create(
            title=title, description=description, customer=customer,
            agent=SupportAgent.objects.get(pk=agent_id) if agent_id else None,
            sla=SLA.objects.get(pk=sla_id) if sla_id else None,
            equipment=Equipment.objects.get(pk=equipment_id) if equipment_id else None,
            category=category, priority=priority,
            attachment=attachment,
            status='Asignado' if agent_id else 'Abierto')
        add_history(ticket, user, 'Creación', new_st=ticket.status, comment='Ticket creado')
        audit(request, 'CREATE', 'Ticket', ticket.id, f'Ticket {ticket.code} creado')
        messages.success(request, f'Ticket {ticket.code} creado correctamente.')
        return redirect(f'/tickets/{ticket.pk}/')

    return _ticket_form_ctx(request, 'Nuevo Ticket')


def _ticket_form_ctx(request, title, ticket=None):
    user = request.user
    return render(request, 'ticket_form.html', {
        'title':            title,
        'ticket':           ticket,
        'category_choices': Ticket.CATEGORY_CHOICES,
        'priority_choices': Ticket.PRIORITY_CHOICES,
        'status_choices':   Ticket.STATUS_CHOICES,
        'slas':             SLA.objects.filter(is_active=True),
        'equipments':       Equipment.objects.all(),
        'customers':  Customer.objects.filter(is_active=True) if is_agent_or_higher(user) else None,
        'agents':     SupportAgent.objects.filter(is_available=True) if is_supervisor_or_admin(user) else None,
    })


@login_required
def ticket_detail_view(request, pk):
    user   = request.user
    ticket = get_object_or_404(Ticket, pk=pk, is_deleted=False)

    # Control de acceso
    if is_customer(user) and ticket.customer != user.customer:
        messages.error(request, 'No tienes permiso para ver este ticket.')
        return redirect('/tickets/')
    if is_agent(user) and not is_supervisor_or_admin(user) and ticket.agent != user.support_agent:
        messages.error(request, 'Solo puedes ver los tickets asignados a ti.')
        return redirect('/tickets/')

    if request.method == 'POST':
        content    = request.POST.get('content', '').strip()
        attachment = request.FILES.get('attachment')
        if not content or len(content) < 3:
            messages.error(request, 'El comentario debe tener al menos 3 caracteres.')
            return redirect(f'/tickets/{pk}/')
        TicketComment.objects.create(ticket=ticket, user=user, content=content, attachment=attachment)
        if not ticket.first_response_at and is_agent_or_higher(user):
            ticket.first_response_at = timezone.now()
            ticket.save(update_fields=['first_response_at'])
        add_history(ticket, user, 'Comentario', comment=content[:100])
        messages.success(request, 'Comentario agregado.')
        return redirect(f'/tickets/{pk}/')

    return render(request, 'ticket_detail.html', {
        'ticket':            ticket,
        'comments':          ticket.comments.select_related('user').all(),
        'history':           ticket.history.select_related('user').all(),
        'agents':            SupportAgent.objects.filter(is_available=True),
        'status_choices':    Ticket.STATUS_CHOICES,
        'can_assign':        is_supervisor_or_admin(user),
        'can_change_status': is_agent_or_higher(user),
    })


@login_required
def ticket_edit_view(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, is_deleted=False)
    user   = request.user

    if is_customer(user):
        messages.error(request, 'Los clientes no pueden editar tickets.')
        return redirect(f'/tickets/{pk}/')

    if request.method == 'POST':
        title        = request.POST.get('title', '').strip()
        description  = request.POST.get('description', '').strip()
        category     = request.POST.get('category', ticket.category)
        priority     = request.POST.get('priority', ticket.priority)
        sla_id       = request.POST.get('sla')
        equipment_id = request.POST.get('equipment')
        customer_id  = request.POST.get('customer')

        errors = []
        if not title or len(title) < 5:
            errors.append('El título debe tener al menos 5 caracteres.')
        if not description or len(description) < 10:
            errors.append('La descripción debe tener al menos 10 caracteres.')
        if errors:
            for e in errors:
                messages.error(request, e)
            return _ticket_form_ctx(request, 'Editar Ticket', ticket)

        old_priority    = ticket.priority
        ticket.title    = title
        ticket.description = description
        ticket.category = category

        if is_supervisor_or_admin(user):
            ticket.priority = priority
            if sla_id:
                ticket.sla = SLA.objects.get(pk=sla_id)
            if customer_id:
                ticket.customer = get_object_or_404(Customer, pk=customer_id, is_active=True)

        if equipment_id:
            ticket.equipment = Equipment.objects.get(pk=equipment_id)
        ticket.save()

        if old_priority != ticket.priority:
            add_history(ticket, user, 'Cambio de prioridad',
                        old_val=old_priority, new_val=ticket.priority)
        audit(request, 'UPDATE', 'Ticket', pk, f'Ticket {ticket.code} editado')
        messages.success(request, 'Ticket actualizado.')
        return redirect(f'/tickets/{pk}/')

    return _ticket_form_ctx(request, 'Editar Ticket', ticket)


@login_required
@user_passes_test(is_admin)
def ticket_delete_view(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, is_deleted=False)
    if request.method == 'POST':
        ticket.is_deleted = True
        ticket.deleted_at = timezone.now()
        ticket.save()
        add_history(ticket, request.user, 'Eliminación lógica')
        audit(request, 'DELETE', 'Ticket', pk, f'Ticket {ticket.code} eliminado')
        messages.success(request, f'Ticket {ticket.code} eliminado.')
        return redirect('/tickets/')
    return render(request, 'confirm_delete.html', {'object': ticket, 'back_url': '/tickets/'})


# ─── AJAX: cambio de estado ───────────────────────────────────────────────────

@login_required
@require_POST
def ticket_change_status(request, pk):
    if not is_agent_or_higher(request.user):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)

    ticket = get_object_or_404(Ticket, pk=pk, is_deleted=False)
    user   = request.user

    # Agente solo sus tickets
    if is_agent(user) and not is_supervisor_or_admin(user) and ticket.agent != user.support_agent:
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    new_status = data.get('status', '')
    comment    = data.get('comment', '')

    if new_status not in [s[0] for s in Ticket.STATUS_CHOICES]:
        return JsonResponse({'ok': False, 'error': 'Estado inválido'}, status=400)

    old_status    = ticket.status
    ticket.status = new_status
    now           = timezone.now()

    if new_status == 'Resuelto' and not ticket.resolved_at:
        ticket.resolved_at = now
    if new_status == 'Validado' and not ticket.validated_at:
        ticket.validated_at = now
    if new_status == 'Cerrado':
        ticket.closed_at = now
        ticket.closed_by = user

    ticket.save()
    add_history(ticket, user, 'Cambio de estado',
                old_st=old_status, new_st=new_status, comment=comment)
    audit(request, 'STATUS_CHANGE', 'Ticket', pk, f'{old_status} → {new_status}')
    return JsonResponse({'ok': True, 'new_status': new_status})


# ─── AJAX: actualizar prioridad (drag&drop lista de tickets) ──────────────────

@login_required
@require_POST
def ticket_update_priority(request):
    if not is_agent_or_higher(request.user):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    ticket_id    = data.get('ticket_id')
    new_priority = data.get('priority')

    if new_priority not in [p[0] for p in Ticket.PRIORITY_CHOICES]:
        return JsonResponse({'ok': False, 'error': 'Prioridad inválida'}, status=400)

    ticket = get_object_or_404(Ticket, pk=ticket_id, is_deleted=False)

    # Agente solo puede cambiar prioridad de sus tickets
    if is_agent(request.user) and not is_supervisor_or_admin(request.user):
        if ticket.agent != request.user.support_agent:
            return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)

    old_priority    = ticket.priority
    ticket.priority = new_priority
    ticket.save(update_fields=['priority'])
    add_history(ticket, request.user, 'Cambio de prioridad',
                old_val=old_priority, new_val=new_priority)
    audit(request, 'PRIORITY_UPDATE', 'Ticket', ticket.id,
          f'Prioridad: {old_priority} → {new_priority}')
    return JsonResponse({'ok': True})


# ─── AJAX: asignar agente ─────────────────────────────────────────────────────

@login_required
@require_POST
def ticket_assign_agent(request, pk):
    if not is_supervisor_or_admin(request.user):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)

    ticket = get_object_or_404(Ticket, pk=pk, is_deleted=False)
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    agent_id  = data.get('agent_id')
    old_agent = str(ticket.agent) if ticket.agent else 'Sin asignar'

    if agent_id:
        agent        = get_object_or_404(SupportAgent, pk=agent_id)
        ticket.agent = agent
        ticket.status = 'Asignado'
        if not ticket.first_response_at:
            ticket.first_response_at = timezone.now()
        new_agent = str(agent)
    else:
        ticket.agent  = None
        ticket.status = 'Abierto'
        new_agent     = 'Sin asignar'

    ticket.save()
    add_history(ticket, request.user, 'Asignación de agente',
                old_val=old_agent, new_val=new_agent)
    audit(request, 'ASSIGN', 'Ticket', pk, f'Agente: {old_agent} → {new_agent}')
    return JsonResponse({'ok': True, 'agent': new_agent, 'status': ticket.status})


# ─── Kanban ───────────────────────────────────────────────────────────────────


# ─── Calendario ───────────────────────────────────────────────────────────────

@login_required
def calendar_view(request):
    if not is_agent_or_higher(request.user):
        return redirect('/tickets/')
    return render(request, 'calendar.html')


@login_required
def calendar_events_view(request):
    if request.method == 'GET':
        color_map = {
            'Mantenimiento': '#0d6efd', 'Interrupción': '#dc3545',
            'Actualización': '#198754', 'Otro': '#6c757d',
        }
        data = [{
            'id': e.pk, 'title': e.title,
            'start': e.start_time.isoformat(), 'end': e.end_time.isoformat(),
            'color': color_map.get(e.event_type, '#0d6efd'),
            'extendedProps': {'description': e.description, 'event_type': e.event_type},
        } for e in MaintenanceEvent.objects.all()]
        return JsonResponse(data, safe=False)

    if not is_agent_or_higher(request.user):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)

    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    title      = data.get('title', '').strip()
    start_time = data.get('start_time', '')
    end_time   = data.get('end_time', '')
    if not all([title, start_time, end_time]):
        return JsonResponse({'ok': False, 'error': 'Título, inicio y fin son obligatorios.'}, status=400)

    event = MaintenanceEvent.objects.create(
        title=title, description=data.get('description', ''),
        start_time=start_time, end_time=end_time,
        event_type=data.get('event_type', 'Mantenimiento'),
        created_by=request.user)
    audit(request, 'CREATE', 'MaintenanceEvent', event.id, f'Evento {title} creado')
    return JsonResponse({'ok': True, 'id': event.pk})


@login_required
@require_http_methods(["GET", "POST", "PUT", "PATCH"])
def calendar_event_update(request, pk):
    if not is_agent_or_higher(request.user):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    event = get_object_or_404(MaintenanceEvent, pk=pk)
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST
    event.title       = data.get('title',       event.title)
    event.description = data.get('description', event.description)
    event.event_type  = data.get('event_type',  event.event_type)
    if data.get('start_time'):
        event.start_time = data['start_time']
    if data.get('end_time'):
        event.end_time = data['end_time']
    event.save()
    audit(request, 'UPDATE', 'MaintenanceEvent', pk, f'Evento {event.title} actualizado')
    return JsonResponse({'ok': True})


@login_required
@require_http_methods(["POST", "DELETE"])
def calendar_event_delete(request, pk):
    if not is_agent_or_higher(request.user):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    event = get_object_or_404(MaintenanceEvent, pk=pk)
    title = event.title
    event.delete()
    audit(request, 'DELETE', 'MaintenanceEvent', pk, f'Evento {title} eliminado')
    return JsonResponse({'ok': True})


@login_required
@require_POST
def calendar_event_move(request, pk):
    if not is_agent_or_higher(request.user):
        return JsonResponse({'ok': False, 'error': 'Sin permiso'}, status=403)
    event = get_object_or_404(MaintenanceEvent, pk=pk)
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST
    if data.get('start'):
        event.start_time = data['start']
    if data.get('end'):
        event.end_time = data['end']
    event.save()
    return JsonResponse({'ok': True})


# ─── Reportes ─────────────────────────────────────────────────────────────────

@login_required
def reports_view(request):
    if not is_agent_or_higher(request.user):
        return redirect('/tickets/')

    qs = Ticket.objects.filter(is_deleted=False)
    if is_agent(request.user) and not is_supervisor_or_admin(request.user):
        qs = qs.filter(agent=request.user.support_agent)

    date_from = request.GET.get('date_from')
    date_to   = request.GET.get('date_to')
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    total    = qs.count()
    resolved = qs.filter(resolved_at__isnull=False).count()
    overdue  = qs.filter(due_date__lt=timezone.now()).exclude(
                   status__in=['Resuelto', 'Cerrado', 'Validado']).count()
    sla_ok   = qs.filter(resolved_at__isnull=False, resolved_at__lte=F('due_date')).count()
    sla_pct  = round((sla_ok / resolved) * 100, 1) if resolved else 0

    resolved_list = list(qs.filter(resolved_at__isnull=False).values('resolved_at', 'created_at'))
    mttr = round(
        sum((t['resolved_at'] - t['created_at']).total_seconds() for t in resolved_list)
        / len(resolved_list) / 3600, 1) if resolved_list else 0

    categories = list(qs.values('category').annotate(total=Count('id')).order_by('-total'))
    monthly    = list(qs.annotate(month=TruncMonth('created_at'))
                       .values('month').annotate(total=Count('id')).order_by('month'))

    return render(request, 'reports.html', {
        'total': total, 'resolved': resolved, 'overdue': overdue,
        'sla_pct': sla_pct, 'mttr': mttr,
        'categories': json.dumps(categories, default=str),
        'monthly':    json.dumps(monthly,    default=str),
        'date_from':  date_from or '',
        'date_to':    date_to   or '',
    })


# ─── Auditoría ────────────────────────────────────────────────────────────────


