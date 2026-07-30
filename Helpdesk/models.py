from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


# ─────────────────────────────────────────────────────────────
#  Customer
# ─────────────────────────────────────────────────────────────
class Customer(models.Model):
    user        = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer')
    full_name   = models.CharField(max_length=150, default='')
    phone       = models.CharField(max_length=20, blank=True)
    company     = models.CharField(max_length=100, blank=True)
    department  = models.CharField(max_length=100, blank=True)
    position    = models.CharField(max_length=100, blank=True)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering            = ['full_name']

    def __str__(self):
        return self.full_name or self.user.username


# ─────────────────────────────────────────────────────────────
#  SupportAgent
# ─────────────────────────────────────────────────────────────
class SupportAgent(models.Model):
    ROLE_CHOICES = [
        ('Analista',    'Analista'),
        ('Especialista','Especialista'),
        ('Supervisor',  'Supervisor'),
    ]
    SPECIALITIES = [
        ('Redes',        'Redes'),
        ('Hardware',     'Hardware'),
        ('Software',     'Software'),
        ('Bases de datos','Bases de datos'),
        ('Servidores',   'Servidores'),
        ('Seguridad',    'Seguridad'),
        ('Otros',        'Otros'),
    ]
    user         = models.OneToOneField(User, on_delete=models.CASCADE, related_name='support_agent')
    role         = models.CharField(max_length=50, choices=ROLE_CHOICES, default='Analista')
    speciality   = models.CharField(max_length=50, choices=SPECIALITIES, default='Otros')
    extension    = models.CharField(max_length=20, blank=True)
    is_available = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Agente'
        verbose_name_plural = 'Agentes'
        ordering            = ['user__first_name']

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    @property
    def is_supervisor(self):
        return self.role == 'Supervisor'


# ─────────────────────────────────────────────────────────────
#  SLA
# ─────────────────────────────────────────────────────────────
class SLA(models.Model):
    name                  = models.CharField(max_length=50, unique=True)
    response_time_hours   = models.PositiveIntegerField(default=4)
    resolution_time_hours = models.PositiveIntegerField(default=24)
    description           = models.TextField(blank=True)
    is_active             = models.BooleanField(default=True)
    created_at            = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'SLA'
        verbose_name_plural = 'SLAs'
        ordering            = ['name']

    def __str__(self):
        return self.name


# ─────────────────────────────────────────────────────────────
#  Equipment
# ─────────────────────────────────────────────────────────────
class Equipment(models.Model):
    TYPES = [
        ('Laptop',    'Laptop'),
        ('Desktop',   'Desktop'),
        ('Servidor',  'Servidor'),
        ('Impresora', 'Impresora'),
        ('Router',    'Router'),
        ('Switch',    'Switch'),
        ('Otro',      'Otro'),
    ]
    STATUS = [
        ('Operativo',         'Operativo'),
        ('En reparación',     'En reparación'),
        ('Fuera de servicio', 'Fuera de servicio'),
    ]
    name            = models.CharField(max_length=100)
    equipment_type  = models.CharField(max_length=50, choices=TYPES, default='Otro')
    serial_number   = models.CharField(max_length=100, unique=True)
    status          = models.CharField(max_length=20, choices=STATUS, default='Operativo')
    owner           = models.ForeignKey(Customer,     on_delete=models.SET_NULL, null=True, blank=True, related_name='equipment')
    assigned_agent  = models.ForeignKey(SupportAgent, on_delete=models.SET_NULL, null=True, blank=True, related_name='equipment')
    purchase_date   = models.DateField(blank=True, null=True)
    description     = models.TextField(blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Equipo'
        verbose_name_plural = 'Equipos'
        ordering            = ['name']

    def __str__(self):
        return f'{self.name} ({self.serial_number})'


# ─────────────────────────────────────────────────────────────
#  Ticket
# ─────────────────────────────────────────────────────────────
class Ticket(models.Model):
    STATUS_CHOICES = [
        ('Abierto',    'Abierto'),
        ('Asignado',   'Asignado'),
        ('En proceso', 'En proceso'),
        ('Pendiente',  'Pendiente'),
        ('Resuelto',   'Resuelto'),
        ('Validado',   'Validado'),
        ('Cerrado',    'Cerrado'),
    ]
    PRIORITY_CHOICES = [
        ('Baja',    'Baja'),
        ('Media',   'Media'),
        ('Alta',    'Alta'),
        ('Crítica', 'Crítica'),
    ]
    CATEGORY_CHOICES = [
        ('Hardware',           'Hardware'),
        ('Software',           'Software'),
        ('Red',                'Red'),
        ('Internet',           'Internet'),
        ('Correo electrónico', 'Correo electrónico'),
        ('Servidores',         'Servidores'),
        ('Bases de datos',     'Bases de datos'),
        ('Seguridad',          'Seguridad'),
        ('Otros',              'Otros'),
    ]

    code             = models.CharField(max_length=20, unique=True, blank=True)
    title            = models.CharField(max_length=200)
    description      = models.TextField()
    customer         = models.ForeignKey(Customer,     on_delete=models.CASCADE,   related_name='tickets')
    agent            = models.ForeignKey(SupportAgent, on_delete=models.SET_NULL,  null=True, blank=True, related_name='tickets')
    sla              = models.ForeignKey(SLA,          on_delete=models.SET_NULL,  null=True, blank=True)
    equipment        = models.ForeignKey(Equipment,    on_delete=models.SET_NULL,  null=True, blank=True, related_name='tickets')
    category         = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Otros')
    priority         = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='Media')
    status           = models.CharField(max_length=20, choices=STATUS_CHOICES,   default='Abierto')
    attachment       = models.FileField(upload_to='tickets/', blank=True, null=True)
    resolution_notes = models.TextField(blank=True)

    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)
    first_response_at= models.DateTimeField(blank=True, null=True)
    resolved_at      = models.DateTimeField(blank=True, null=True)
    validated_at     = models.DateTimeField(blank=True, null=True)
    closed_at        = models.DateTimeField(blank=True, null=True)
    closed_by        = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='closed_tickets')
    due_date         = models.DateTimeField(blank=True, null=True)

    # Eliminación lógica
    is_deleted  = models.BooleanField(default=False)
    deleted_at  = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name        = 'Ticket'
        verbose_name_plural = 'Tickets'
        ordering            = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.code:
            last = Ticket.objects.order_by('id').last()
            next_id = (last.id + 1) if last else 1
            self.code = f'TICK-{next_id:06d}'

        if not self.sla:
            default_sla, _ = SLA.objects.get_or_create(
                name='Normal',
                defaults={'response_time_hours': 4, 'resolution_time_hours': 24}
            )
            self.sla = default_sla

        if self.sla and not self.due_date:
            self.due_date = timezone.now() + timezone.timedelta(hours=self.sla.resolution_time_hours)

        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.code} - {self.title}'

    @property
    def is_overdue(self):
        if self.due_date and self.status not in ('Resuelto', 'Cerrado', 'Validado'):
            return timezone.now() > self.due_date
        return False

    @property
    def sla_status(self):
        if self.resolved_at and self.due_date:
            return 'Cumplido' if self.resolved_at <= self.due_date else 'Incumplido'
        return 'Pendiente'


# ─────────────────────────────────────────────────────────────
#  TicketHistory
# ─────────────────────────────────────────────────────────────
class TicketHistory(models.Model):
    ticket     = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='history')
    user       = models.ForeignKey(User,   on_delete=models.SET_NULL, null=True)
    action     = models.CharField(max_length=100, blank=True)
    old_value  = models.CharField(max_length=200, blank=True)
    new_value  = models.CharField(max_length=200, blank=True)
    old_status = models.CharField(max_length=20,  blank=True)
    new_status = models.CharField(max_length=20,  blank=True)
    comment    = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Historial de Ticket'
        verbose_name_plural = 'Historial de Tickets'
        ordering            = ['-created_at']

    def __str__(self):
        return f'{self.ticket.code} – {self.action} – {self.created_at:%Y-%m-%d %H:%M}'


# ─────────────────────────────────────────────────────────────
#  TicketComment
# ─────────────────────────────────────────────────────────────
class TicketComment(models.Model):
    ticket     = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments')
    user       = models.ForeignKey(User,   on_delete=models.CASCADE)
    content    = models.TextField()
    attachment = models.FileField(upload_to='comments/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Comentario'
        verbose_name_plural = 'Comentarios'
        ordering            = ['created_at']

    def __str__(self):
        return f'Comentario en {self.ticket.code} por {self.user.username}'


# ─────────────────────────────────────────────────────────────
#  MaintenanceEvent
# ─────────────────────────────────────────────────────────────
class MaintenanceEvent(models.Model):
    EVENT_TYPES = [
        ('Mantenimiento', 'Mantenimiento'),
        ('Interrupción',  'Interrupción'),
        ('Actualización', 'Actualización'),
        ('Otro',          'Otro'),
    ]
    title       = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_time  = models.DateTimeField()
    end_time    = models.DateTimeField()
    event_type  = models.CharField(max_length=20, choices=EVENT_TYPES, default='Mantenimiento')
    color       = models.CharField(max_length=20, default='#0d6efd')
    created_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Evento de Mantenimiento'
        verbose_name_plural = 'Eventos de Mantenimiento'
        ordering            = ['-start_time']

    def __str__(self):
        return self.title


# ─────────────────────────────────────────────────────────────
#  AuditLog
# ─────────────────────────────────────────────────────────────
class AuditLog(models.Model):
    user       = models.ForeignKey(User,   on_delete=models.SET_NULL, null=True, blank=True)
    action     = models.CharField(max_length=100)
    entity     = models.CharField(max_length=50)
    entity_id  = models.PositiveIntegerField(null=True, blank=True)
    detail     = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Log de Auditoría'
        verbose_name_plural = 'Logs de Auditoría'
        ordering            = ['-created_at']

    def __str__(self):
        username = self.user.username if self.user else 'Anónimo'
        return f'[{self.created_at:%Y-%m-%d %H:%M}] {username} – {self.action} – {self.entity}'
