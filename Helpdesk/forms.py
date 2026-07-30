import re
from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Customer, SLA, Equipment, Ticket, TicketComment, MaintenanceEvent


# ─── Validadores reutilizables ────────────────────────────────────────────────

def validate_only_letters(value):
    if value and not re.match(r'^[A-Za-záéíóúÁÉÍÓÚñÑüÜ\s\-]+$', value):
        raise ValidationError('Solo se permiten letras, espacios y guiones.')

def validate_phone(value):
    if value and not re.match(r'^[\d\+\-\s\(\)]{7,20}$', value):
        raise ValidationError('Teléfono inválido. Use dígitos, +, -, espacios o paréntesis (7-20 caracteres).')

def validate_username(value):
    if value and not re.match(r'^[A-Za-z0-9_\.\-]{3,150}$', value):
        raise ValidationError('El usuario solo puede contener letras, números, puntos, guiones y _ (3-150 caracteres).')

def validate_serial(value):
    if value and not re.match(r'^[A-Za-z0-9\-\_\.]{3,50}$', value):
        raise ValidationError('El serial solo puede contener letras, números, guiones y puntos (3-50 caracteres).')


# ─── Formulario de Cliente ────────────────────────────────────────────────────

class CustomerForm(forms.Form):
    username = forms.CharField(
        max_length=150, label='Usuario',
        validators=[validate_username],
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'usuario123'})
    )
    password = forms.CharField(
        required=False, label='Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control',
                                          'placeholder': 'Dejar en blanco para no cambiar'})
    )
    email = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    full_name = forms.CharField(
        max_length=150, label='Nombre completo',
        validators=[validate_only_letters],
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    phone = forms.CharField(
        max_length=20, required=False, label='Teléfono',
        validators=[validate_phone],
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+593 99 000 0000'})
    )
    company = forms.CharField(
        max_length=100, required=False, label='Empresa',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    department = forms.CharField(
        max_length=100, required=False, label='Departamento',
        validators=[validate_only_letters],
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    position = forms.CharField(
        max_length=100, required=False, label='Cargo',
        validators=[validate_only_letters],
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    is_active = forms.BooleanField(
        required=False, initial=True, label='Activo',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def clean_password(self):
        pwd = self.cleaned_data.get('password', '')
        # Solo valida longitud si se ingresó una contraseña nueva
        if pwd and len(pwd) < 8:
            raise ValidationError('La contraseña debe tener al menos 8 caracteres.')
        return pwd


# ─── Formulario de SLA ────────────────────────────────────────────────────────

class SLAForm(forms.ModelForm):
    class Meta:
        model  = SLA
        fields = ['name', 'response_time_hours', 'resolution_time_hours', 'description', 'is_active']
        widgets = {
            'name':                  forms.TextInput(attrs={'class': 'form-control'}),
            'response_time_hours':   forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'resolution_time_hours': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'description':           forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active':             forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name':                  'Nombre del SLA',
            'response_time_hours':   'Tiempo de respuesta (horas)',
            'resolution_time_hours': 'Tiempo de resolución (horas)',
            'description':           'Descripción',
            'is_active':             'Activo',
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise ValidationError('El nombre del SLA es obligatorio.')
        return name

    def clean_response_time_hours(self):
        v = self.cleaned_data.get('response_time_hours')
        if v is not None and v < 1:
            raise ValidationError('El tiempo de respuesta debe ser al menos 1 hora.')
        return v

    def clean_resolution_time_hours(self):
        v = self.cleaned_data.get('resolution_time_hours')
        if v is not None and v < 1:
            raise ValidationError('El tiempo de resolución debe ser al menos 1 hora.')
        return v


# ─── Formulario de Equipo ─────────────────────────────────────────────────────

class EquipmentForm(forms.ModelForm):
    class Meta:
        model  = Equipment
        fields = ['name', 'equipment_type', 'serial_number', 'status',
                  'owner', 'purchase_date', 'description']
        widgets = {
            'name':          forms.TextInput(attrs={'class': 'form-control'}),
            'equipment_type':forms.Select(attrs={'class': 'form-select'}),
            'serial_number': forms.TextInput(attrs={'class': 'form-control'}),
            'status':        forms.Select(attrs={'class': 'form-select'}),
            'owner':         forms.Select(attrs={'class': 'form-select select2'}),
            'purchase_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'description':   forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean_serial_number(self):
        serial = self.cleaned_data.get('serial_number', '').strip()
        validate_serial(serial)
        return serial

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise ValidationError('El nombre del equipo es obligatorio.')
        return name


# ─── Formulario de Ticket ─────────────────────────────────────────────────────

class TicketForm(forms.ModelForm):
    class Meta:
        model  = Ticket
        fields = ['title', 'description', 'customer', 'sla',
                  'equipment', 'category', 'priority', 'attachment']
        widgets = {
            'title':       forms.TextInput(attrs={
                               'class': 'form-control',
                               'placeholder': 'Resumen breve del problema'}),
            'description': forms.Textarea(attrs={
                               'class': 'form-control', 'rows': 5,
                               'placeholder': 'Describe el problema con detalle'}),
            'customer':    forms.Select(attrs={'class': 'form-select select2'}),
            'sla':         forms.Select(attrs={'class': 'form-select select2'}),
            'equipment':   forms.Select(attrs={'class': 'form-select select2'}),
            'category':    forms.Select(attrs={'class': 'form-select'}),
            'priority':    forms.Select(attrs={'class': 'form-select'}),
            'attachment':  forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()
        if len(title) < 5:
            raise ValidationError('El título debe tener al menos 5 caracteres.')
        return title

    def clean_description(self):
        desc = self.cleaned_data.get('description', '').strip()
        if len(desc) < 10:
            raise ValidationError('La descripción debe tener al menos 10 caracteres.')
        return desc


# ─── Formulario de Comentario ─────────────────────────────────────────────────

class CommentForm(forms.ModelForm):
    class Meta:
        model  = TicketComment
        fields = ['content', 'attachment']
        widgets = {
            'content':    forms.Textarea(attrs={
                              'class': 'form-control', 'rows': 3,
                              'placeholder': 'Escribe tu comentario aquí...'}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'content':    'Comentario',
            'attachment': 'Adjunto (opcional)',
        }

    def clean_content(self):
        content = self.cleaned_data.get('content', '').strip()
        if len(content) < 3:
            raise ValidationError('El comentario debe tener al menos 3 caracteres.')
        if len(content) > 2000:
            raise ValidationError('El comentario no puede superar los 2000 caracteres.')
        return content


# ─── Formulario de Evento de Mantenimiento ────────────────────────────────────

class MaintenanceEventForm(forms.ModelForm):
    class Meta:
        model  = MaintenanceEvent
        fields = ['title', 'description', 'start_time', 'end_time', 'event_type', 'color']
        widgets = {
            'title':       forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'start_time':  forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_time':    forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'event_type':  forms.Select(attrs={'class': 'form-select'}),
            'color':       forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
        }

    def clean(self):
        cleaned = super().clean()
        start   = cleaned.get('start_time')
        end     = cleaned.get('end_time')
        if start and end and end <= start:
            raise ValidationError('La fecha de fin debe ser posterior a la de inicio.')
        return cleaned

    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()
        if not title:
            raise ValidationError('El título del evento es obligatorio.')
        return title
