from rest_framework.routers import DefaultRouter

from .views import BookingViewSet, EventViewSet, OrganizerBookingViewSet

router = DefaultRouter()
router.register('events', EventViewSet, basename='event')
router.register('bookings', BookingViewSet, basename='booking')
router.register('organizer/bookings', OrganizerBookingViewSet, basename='organizer-booking')

urlpatterns = router.urls
