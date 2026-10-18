from django.db.models import Sum
from rest_framework import serializers

from .models import Booking, Event


class EventSerializer(serializers.ModelSerializer):
    organizer = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Event
        fields = [
            'id',
            'organizer',
            'title',
            'description',
            'location',
            'start_time',
            'end_time',
            'capacity',
            'is_cancelled',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'organizer', 'is_cancelled', 'created_at', 'updated_at']

    def validate(self, attrs):
        start_time = attrs.get('start_time', getattr(self.instance, 'start_time', None))
        end_time = attrs.get('end_time', getattr(self.instance, 'end_time', None))
        if start_time and end_time and end_time <= start_time:
            raise serializers.ValidationError('end_time must be after start_time')
        return attrs


class BookingSerializer(serializers.ModelSerializer):
    customer = serializers.StringRelatedField(read_only=True)
    event_title = serializers.CharField(source='event.title', read_only=True)

    class Meta:
        model = Booking
        fields = ['id', 'event', 'event_title', 'customer', 'quantity', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'customer', 'status', 'created_at', 'updated_at']

    def validate(self, attrs):
        event = attrs['event']
        quantity = attrs['quantity']
        if event.is_cancelled:
            raise serializers.ValidationError('Cannot book a cancelled event.')

        active_tickets = event.bookings.filter(status=Booking.Status.ACTIVE).aggregate(
            total=Sum('quantity')
        )['total'] or 0
        if active_tickets + quantity > event.capacity:
            raise serializers.ValidationError('Not enough seats available.')
        return attrs
