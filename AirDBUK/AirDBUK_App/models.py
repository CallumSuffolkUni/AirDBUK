from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Airport (models.Model):
    id = models.AutoField(primary_key=True) #Auto assign primary_key
    City = models.CharField(max_length=255  , default='')
    IATA_Code = models.CharField(max_length=3, default='')
    Name = models.CharField(max_length=100, default='')

    class Meta :
        verbose_name = 'Airport'
        verbose_name_plural = 'Airports'

    def __str__(self):
        return f'{self.City}, {self.IATA_Code}, ({self.Name})'


class Flight (models.Model):
    id = models.AutoField(primary_key=True) #Auto assign primary_key
    Flight_Number = models.CharField(max_length=7, unique=True)
    Departure_Time = models.DateTimeField()
    Arrival_Time = models.DateTimeField()
    Status = models.CharField(max_length=100, default='Scheduled')
    Travel_Class = models.CharField(max_length=20, default='Economy')
    Price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    Departure_Airport = models.ForeignKey(Airport, on_delete=models.SET_NULL, null = True, blank = True, related_name = "departing_flights")
    Arrival_Airport = models.ForeignKey(Airport, on_delete=models.SET_NULL, null = True, blank = True, related_name = "arriving_flights")

    class Meta :
        verbose_name = 'Flight'
        verbose_name_plural = 'Flights'

    def __str__(self):
        return f'{self.Flight_Number} - {self.Departure_Airport} → {self.Arrival_Airport}'

class Booking (models.Model):
    id = models.AutoField(primary_key=True) #Auto assign primary_key
    Booking_Date = models.DateTimeField()
    Status = models.CharField(max_length=100, default='')
    Total_Price = models.DecimalField(max_digits=10, decimal_places=2)
    Flight_ID = models.ForeignKey(Flight, on_delete=models.SET_NULL, null = True, blank = True, related_name = "bookings") #Foreign Key linking to flight table
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')

    class Meta:
        verbose_name = 'Booking'
        verbose_name_plural = 'Bookings'


class Passenger (models.Model):
    id = models.AutoField(primary_key=True) #Auto assign primary_key
    First_Name = models.CharField(max_length=100, default='')
    Last_Name = models.CharField(max_length=100, default='')
    DOB = models.DateField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='passengers')

    class Meta:
        verbose_name = 'Passenger'
        verbose_name_plural = 'Passengers'

    def __str__(self):
        return f'{self.First_Name} {self.Last_Name}'


class Booking_Passenger (models.Model):
    id = models.AutoField(primary_key=True) #Auto assign primary_key
    Booking_ID = models.ForeignKey(Booking, on_delete=models.SET_NULL, null = True, blank = True, related_name = "booking_passengers") #Foreign Key linking to booking table
    Passenger_ID = models.ForeignKey(Passenger, on_delete=models.SET_NULL, null = True, blank = True, related_name = "booking_passengers") #Foreign Key linking to passernger table

    class Meta:
        verbose_name = "Booking_Passenger"
        verbose_name_plural = "Booking_Passengers"