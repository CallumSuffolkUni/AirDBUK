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
            'class': 'autocomplete form-input',
            'list': 'departure-list',
            'autocomplete': 'off',
        })
    )
    arrival_airport = forms.CharField(
        label="To",
        widget=forms.TextInput(attrs={
            'placeholder': 'Type arrival airport',
            'class': 'autocomplete form-input',
            'list': 'arrival-list',
            'autocomplete': 'off',
        })
    )
    departure_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-input',
        }),
        label="Departure",
        initial=date.today
    )
    travel_class = forms.ChoiceField(  
        choices=TRAVEL_CLASS_CHOICES,
        label="Travel Class",
        widget=forms.Select(attrs={'class': 'form-input'})
    )
    passengers = forms.IntegerField(
        min_value=1,
        initial=1,
        label="Passengers",
        widget=forms.NumberInput(attrs={'class': 'form-input'})
    )

class AddPassengerDetails(forms.Form):
    first_name = forms.CharField(
        label="First Name",
        widget=forms.TextInput(attrs={
            "class": "form-input",
            "placeholder": "Enter first name"
        })
    )
    last_name = forms.CharField(
        label="Last Name",
        widget=forms.TextInput(attrs={
            "class": "form-input",
            "placeholder": "Enter last name"
        })
    )
    dob = forms.DateField(
        label="Date of Birth",
        input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(attrs={
            "type": "date",
            "class": "form-input"
        })  
    )

#class 