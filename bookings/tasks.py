from django.conf import settings
from django.core.mail import send_mail

from celery import shared_task

from .models import Booking, Event


@shared_task
def send_booking_confirmation_email(booking_id):
    booking = Booking.objects.select_related('event', 'customer').get(id=booking_id)
    send_mail(
        subject='Booking Confirmation',
        message=f'Your booking for {booking.event.title} is confirmed.',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[booking.customer.email],
        fail_silently=True,
    )


@shared_task
def send_event_update_email(event_id):
    event = Event.objects.get(id=event_id)
    customer_emails = list(
        event.bookings.filter(status=Booking.Status.ACTIVE)
        .select_related('customer')
        .values_list('customer__email', flat=True)
        .distinct()
    )
    customer_emails = [email for email in customer_emails if email]
    if not customer_emails:
        return

    send_mail(
        subject=f'Event Updated: {event.title}',
        message=f'The event "{event.title}" has been updated. Please review latest details.',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=customer_emails,
        fail_silently=True,
    )
