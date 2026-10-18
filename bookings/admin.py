from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Booking, Event, User

admin.site.register(User, UserAdmin)
admin.site.register(Event)
admin.site.register(Booking)

# Register your models here.
