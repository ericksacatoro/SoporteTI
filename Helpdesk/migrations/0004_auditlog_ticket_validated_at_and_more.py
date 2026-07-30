from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('Helpdesk', '0003_alter_ticketcomment_options_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── AuditLog ──────────────────────────────────────────────────────────
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id',         models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action',     models.CharField(max_length=100)),
                ('entity',     models.CharField(max_length=50)),
                ('entity_id',  models.PositiveIntegerField(blank=True, null=True)),
                ('detail',     models.TextField(blank=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user',       models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Log de Auditoría', 'verbose_name_plural': 'Logs de Auditoría', 'ordering': ['-created_at']},
        ),

        # ── Ticket: validated_at ──────────────────────────────────────────────
        migrations.AddField(
            model_name='ticket',
            name='validated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),

        # ── TicketHistory: nuevos campos action/old_value/new_value ───────────
        migrations.AddField(
            model_name='tickethistory',
            name='action',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='tickethistory',
            name='old_value',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='tickethistory',
            name='new_value',
            field=models.CharField(blank=True, max_length=200),
        ),

        # ── SupportAgent: role con choices ────────────────────────────────────
        migrations.AlterField(
            model_name='supportagent',
            name='role',
            field=models.CharField(
                choices=[('Analista', 'Analista'), ('Especialista', 'Especialista'), ('Supervisor', 'Supervisor')],
                default='Analista', max_length=50,
            ),
        ),

        # ── Ticket: estado Validado ────────────────────────────────────────────
        migrations.AlterField(
            model_name='ticket',
            name='status',
            field=models.CharField(
                choices=[
                    ('Abierto', 'Abierto'), ('Asignado', 'Asignado'), ('En proceso', 'En proceso'),
                    ('Pendiente', 'Pendiente'), ('Resuelto', 'Resuelto'), ('Validado', 'Validado'),
                    ('Cerrado', 'Cerrado'),
                ],
                default='Abierto', max_length=20,
            ),
        ),

        # ── MaintenanceEvent: color y created_by ──────────────────────────────
        migrations.AddField(
            model_name='maintenanceevent',
            name='color',
            field=models.CharField(default='#0d6efd', max_length=20),
        ),
        migrations.AddField(
            model_name='maintenanceevent',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='maintenanceevent',
            name='event_type',
            field=models.CharField(
                choices=[
                    ('Mantenimiento', 'Mantenimiento'), ('Interrupción', 'Interrupción'),
                    ('Actualización', 'Actualización'), ('Otro', 'Otro'),
                ],
                default='Mantenimiento', max_length=20,
            ),
        ),
    ]
