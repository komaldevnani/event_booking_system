from django.db import transaction
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Booking, Event, User
from .permissions import IsCustomer, IsOrganizer
from .serializers import BookingSerializer, EventSerializer
from .tasks import send_booking_confirmation_email, send_event_update_email


class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.select_related('organizer').all()
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action in ['update', 'partial_update', 'destroy', 'cancel'] and self.request.user.role == User.Roles.ORGANIZER:
            return queryset.filter(organizer=self.request.user)
        return queryset

    def create(self, request, *args, **kwargs):
        if request.user.role != User.Roles.ORGANIZER:
            return Response({'detail': 'Only organizers can create events.'}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(organizer=self.request.user)

    def perform_update(self, serializer):
        event = serializer.save()
        transaction.on_commit(lambda: send_event_update_email.delay(event.id))

    def update(self, request, *args, **kwargs):
        if request.user.role != User.Roles.ORGANIZER:
            return Response({'detail': 'Only organizers can update events.'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if request.user.role != User.Roles.ORGANIZER:
            return Response({'detail': 'Only organizers can update events.'}, status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if request.user.role != User.Roles.ORGANIZER:
            return Response({'detail': 'Only organizers can delete events.'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'], permission_classes=[IsOrganizer])
    def cancel(self, request, pk=None):
        event = self.get_object()
        event.is_cancelled = True
        event.save(update_fields=['is_cancelled', 'updated_at'])
        return Response({'detail': 'Event cancelled successfully.'})


class BookingViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated, IsCustomer]

    def get_queryset(self):
        return Booking.objects.select_related('event', 'customer').filter(customer=self.request.user)

    def perform_create(self, serializer):
        booking = serializer.save(customer=self.request.user)
        transaction.on_commit(lambda: send_booking_confirmation_email.delay(booking.id))

    def destroy(self, request, *args, **kwargs):
        booking = self.get_object()
        booking.status = Booking.Status.CANCELLED
        booking.save(update_fields=['status', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrganizerBookingViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated, IsOrganizer]

    def get_queryset(self):
        return Booking.objects.select_related('event', 'customer').filter(event__organizer=self.request.user)
