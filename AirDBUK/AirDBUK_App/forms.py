from django import forms
from .models import Airport, Flight, User, Booking, Passenger, Booking_Passenger, Payment
from datetime import date

TRAVEL_CLASS_CHOICES = [
    ('', 'Select travel class'),
    ('Economy', 'Economy'),
    ('Business', 'Business'),
    ('First', 'First'),
]

class FlightSearchForm(forms.Form):
    departure_airport = forms.CharField(
        label="From",
        widget=forms.TextInput(attrs={
            'placeholder': 'Type departure airport',
            'class': 'autocomplete',  # We'll use this in JS
            'list': 'departure-list',
            'autocomplete': 'off',  # turn off browser native suggestions
        })
    )
    arrival_airport = forms.CharField(
        label="To",
        widget=forms.TextInput(attrs={
            'placeholder': 'Type arrival airport',
            'class': 'autocomplete',
            'list': 'arrival-list',
            'autocomplete': 'off',
        })
    )
    departure_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Departure",
        initial=date.today
    )
    travel_class = forms.ChoiceField(  # Fix 2: ChoiceField not ModelChoiceField
        choices=TRAVEL_CLASS_CHOICES,
        label="Travel Class",
    )
    passengers = forms.IntegerField(
        min_value=1,
        initial=1,
        label="Passengers"
    )