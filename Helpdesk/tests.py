from django.contrib.auth.models import Group, User
from django.test import TestCase

from .models import Customer, Equipment, SLA, SupportAgent, Ticket, TicketHistory


class HelpdeskViewsTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='tester', password='secret123')
        self.customer = Customer.objects.create(user=user, company='ACME', phone='0999999999')
        self.agent = SupportAgent.objects.create(user=user, role='Analista', extension='200')
        self.sla = SLA.objects.create(name='Gold', response_time_hours=2, resolution_time_hours=8)
        self.equipment = Equipment.objects.create(name='Laptop', serial_number='SN-001', owner=self.customer)
        Ticket.objects.create(
            title='Falla de red',
            description='No hay conectividad',
            customer=self.customer,
            agent=self.agent,
            sla=self.sla,
            equipment=self.equipment,
            status='Abierto',
            priority='Alta',
            category='Red',
        )

    def test_home_page_loads(self):
        response = self.client.get('/')
        self.assertIn(response.status_code, [200, 302])

    def test_dashboard_page_loads(self):
        response = self.client.get('/dashboard/')
        self.assertIn(response.status_code, [200, 302])

    def test_agent_only_sees_assigned_tickets(self):
        agent_user = User.objects.create_user(username='agente_test', password='secret123')
        group, _ = Group.objects.get_or_create(name='Agente')
        agent_user.groups.add(group)
        agent_profile = SupportAgent.objects.create(user=agent_user, role='Analista', extension='300')

        customer_user = User.objects.create_user(username='cliente_test', password='secret123')
        customer = Customer.objects.create(user=customer_user, company='Beta', phone='0999999998')
        other_ticket = Ticket.objects.create(
            title='Otro problema',
            description='Sin asignación',
            customer=customer,
            agent=None,
            sla=self.sla,
            equipment=self.equipment,
            status='Abierto',
            priority='Media',
            category='Hardware',
        )
        assigned_ticket = Ticket.objects.create(
            title='Problema asignado',
            description='Asignado al agente',
            customer=self.customer,
            agent=agent_profile,
            sla=self.sla,
            equipment=self.equipment,
            status='Abierto',
            priority='Alta',
            category='Software',
        )

        self.client.login(username='agente_test', password='secret123')
        response = self.client.get('/tickets/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, assigned_ticket.title)
        self.assertNotContains(response, other_ticket.title)

    def test_status_change_creates_history_entry(self):
        self.client.login(username='tester', password='secret123')
        ticket = Ticket.objects.get(title='Falla de red')

        response = self.client.post(f'/tickets/{ticket.pk}/status/', {'status': 'En proceso'})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(TicketHistory.objects.filter(ticket=ticket, new_status='En proceso').exists())
