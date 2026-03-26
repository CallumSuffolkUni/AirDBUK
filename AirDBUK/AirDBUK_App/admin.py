from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register([Flight, Booking, Passenger, Booking_Passenger])
