from django.db import models
from phonenumber_field.modelfields import PhoneNumberField

# Create your models here.
class Flight (models.Model):
    id = models.AutoField(primary_key=True) #Auto assign primary_key
    Flight_Number = models.CharField(max_length=6, default='')
    City = models.CharField(max_length=100, default='')
    IATA_Code = models.CharField(max_length=3, default='')
    Departure_Airport = models.CharField(max_length=100, default='')
    Arrival_Airport = models.CharField(max_length=100, default='')
    Departure_Time = models.DateTimeField()
    Arrival_Time = models.DateTimeField()
    Status = models.CharField(max_length=100, default='Scheduled')

    class Meta :
        verbose_name = 'Flight'
        verbose_name_plural = 'Flights'
        constraints = [
            models.UniqueConstraint(fields=['Flight_Number', 'IATA_Code'], name='UniqueFlight'),
        ]

    def __str__(self):
        return f'{self.City} ({self.IATA_Code})'


class User (models.Model):
    id = models.AutoField(primary_key=True) #Auto assign primary_key
    Email = models.EmailField(default='')
    Password = models.CharField(max_length=25, default='')
    First_Name = models.CharField(max_length=100, default='')
    Last_Name = models.CharField(max_length=100, default='')
    Phone = PhoneNumberField()
    Role = models.CharField(max_length=100, default='')

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        constraints = [
            models.UniqueConstraint(fields=['Email', 'Phone'], name='UniqueUser'),
        ]

    def __str__(self):
        return f'{self.First_Name} {self.Last_Name}'


class Booking (models.Model):
    id = models.AutoField(primary_key=True) #Auto assign primary_key
    Booking_Date = models.DateTimeField()
    Status = models.CharField(max_length=100, default='')
    Total_Price = models.DecimalField(max_digits=10, decimal_places=2)
    Flight_ID = models.ForeignKey(Flight, on_delete=models.SET_NULL, null = True, blank = True, related_name = "bookings") #Foreign Key linking to flight table
    User_ID = models.ForeignKey(User, on_delete=models.SET_NULL, null = True, blank = True, related_name = "bookings") #Foreign Key linking to user table

    class Meta:
        verbose_name = 'Booking'
        verbose_name_plural = 'Bookings'


class Passenger (models.Model):
    id = models.AutoField(primary_key=True) #Auto assign primary_key
    First_Name = models.CharField(max_length=100, default='')
    Last_Name = models.CharField(max_length=100, default='')
    DOB = models.DateTimeField()
    User_ID = models.ForeignKey(User, on_delete=models.SET_NULL, null = True, blank = True, related_name = "passengers") #Foreign Key linking to user table

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


class Payment (models.Model):
    id = models.AutoField(primary_key=True) #Auto assign primary_key
    Amount = models.DecimalField(max_digits=7, decimal_places=2)
    Payment_Date = models.DateTimeField()
    Booking_ID = models.ForeignKey(Booking, on_delete=models.SET_NULL, null = True, blank = True, related_name = "payments") #Foreign Key linking to booking table

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"