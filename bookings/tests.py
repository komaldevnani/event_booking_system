from datetime import timedelta
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Booking, Event, User


class EventBookingAPITests(APITestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(
            username='organizer',
            password='pass1234',
            role=User.Roles.ORGANIZER,
            email='org@example.com',
        )
        self.customer = User.objects.create_user(
            username='customer',
            password='pass1234',
            role=User.Roles.CUSTOMER,
            email='customer@example.com',
        )
        self.other_customer = User.objects.create_user(
            username='customer2',
            password='pass1234',
            role=User.Roles.CUSTOMER,
            email='customer2@example.com',
        )
        self.event = Event.objects.create(
            organizer=self.organizer,
            title='Tech Summit',
            description='desc',
            location='Online',
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1, hours=2),
            capacity=10,
        )

    def test_customer_cannot_create_event(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            reverse('event-list'),
            {
                'title': 'Hackathon',
                'description': 'event',
                'location': 'NY',
                'start_time': (timezone.now() + timedelta(days=2)).isoformat(),
                'end_time': (timezone.now() + timedelta(days=2, hours=3)).isoformat(),
                'capacity': 50,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_organizer_can_create_event(self):
        self.client.force_authenticate(self.organizer)
        response = self.client.post(
            reverse('event-list'),
            {
                'title': 'Hackathon',
                'description': 'event',
                'location': 'NY',
                'start_time': (timezone.now() + timedelta(days=2)).isoformat(),
                'end_time': (timezone.now() + timedelta(days=2, hours=3)).isoformat(),
                'capacity': 50,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Event.objects.get(id=response.data['id']).organizer, self.organizer)

    @patch('bookings.views.send_booking_confirmation_email.delay')
    def test_customer_booking_triggers_confirmation_task(self, mock_delay):
        self.client.force_authenticate(self.customer)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse('booking-list'),
                {
                    'event': self.event.id,
                    'quantity': 2,
                },
                format='json',
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        booking = Booking.objects.get(id=response.data['id'])
        mock_delay.assert_called_once_with(booking.id)

    def test_customer_can_only_cancel_own_booking(self):
        booking = Booking.objects.create(event=self.event, customer=self.other_customer, quantity=1)
        self.client.force_authenticate(self.customer)
        response = self.client.delete(reverse('booking-detail', kwargs={'pk': booking.id}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_organizer_can_list_bookings_for_own_events(self):
        Booking.objects.create(event=self.event, customer=self.customer, quantity=1)
        self.client.force_authenticate(self.organizer)
        response = self.client.get(reverse('organizer-booking-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    @patch('bookings.views.send_event_update_email.delay')
    def test_event_update_triggers_update_email_task(self, mock_delay):
        self.client.force_authenticate(self.organizer)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(
                reverse('event-detail', kwargs={'pk': self.event.id}),
                {'title': 'Tech Summit Updated'},
                format='json',
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_delay.assert_called_once_with(self.event.id)
