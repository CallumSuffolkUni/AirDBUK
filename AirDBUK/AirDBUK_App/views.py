from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from .forms import FlightSearchForm
from .models import *

# Create your views here.
def home(request):
    form = FlightSearchForm(request.GET or None)
    flights = []

    if form.is_valid():
        # Fix 3: field names now match the form definition
        from_airport = form.cleaned_data['departure_airport']
        to_airport = form.cleaned_data['arrival_airport']
        departure_date = form.cleaned_data['departure_date']
        travel_class = form.cleaned_data['travel_class']

        flights = Flight.objects.filter(
            Departure_Airport=from_airport,
            Arrival_Airport=to_airport,
            Departure_Time__date=departure_date,
            Travel_Class=travel_class    # Also filter by travel class
        )

    return render(request, 'home.html', {'form': form, 'flights': flights})
