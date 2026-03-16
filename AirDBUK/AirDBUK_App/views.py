from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from .forms import FlightSearchForm
from .models import *

# Create your views here.

def home(request):
    """Render landing page with an empty search form."""
    form = FlightSearchForm()
    return render(request, 'home.html', {'form': form})


def airport_autocomplete(request): # Simply for when searching what airport to depart and arrive at.
    """Return a JSON list of airport descriptions matching the query term."""
    term = request.GET.get('term', '').strip()
    results = []
    if term:
        qs = Airport.objects.filter(
            Q(City__icontains=term) |
            Q(IATA_Code__icontains=term)|
            Q(Name__icontains=term)
        )[:20]
        for a in qs:
            # stringifies the airport using __str__
            results.append(str(a))
    return JsonResponse(results, safe=False)



# helper used by both views

def _perform_search(form):
    """Return queryset of flights matching a valid form, or empty list."""
    if not form.is_valid():
        return []

    # get raw strings from inputs
    from_airport_str = form.cleaned_data['departure_airport']
    to_airport_str = form.cleaned_data['arrival_airport']
    departure_date = form.cleaned_data['departure_date']
    travel_class = form.cleaned_data['travel_class']

    def lookup_airport(value):
        if not value:
            return None
        import re
        # Format is "City, IATA, (Name)" — grab the 3-letter code after the first comma
        m = re.search(r",\s*([A-Z]{3})\s*,", value)
        if m:
            return Airport.objects.filter(IATA_Code__iexact=m.group(1)).first()
        # fallback
        return Airport.objects.filter(
            Q(City__iexact=value) | Q(Name__iexact=value) | Q(IATA_Code__iexact=value)
        ).first()

    from_airport = lookup_airport(from_airport_str)
    to_airport = lookup_airport(to_airport_str)

    return Flight.objects.filter(
        Departure_Airport=from_airport,
        Arrival_Airport=to_airport,
        Departure_Time__date=departure_date,
    )

def search_results(request):
    form = FlightSearchForm(request.GET or None)

    flights = _perform_search(form)
    print("FLIGHTS FOUND:", len(flights) if flights else 0)

    # Add duration to each flight
    for flight in flights:
        diff = flight.Arrival_Time - flight.Departure_Time
        total_minutes = int(diff.total_seconds() // 60)
        flight.duration = f"{total_minutes // 60}h {total_minutes % 60}m"

    return render(request, 'search_results.html', {'form': form, 'flights': flights})


def confirm_flight(request):
    flight_id = request.GET.get('flight_id')
    passengers = int(request.GET.get('passengers', 1))

    flight = get_object_or_404(Flight, id=flight_id)

    # Calculate duration
    diff = flight.Arrival_Time - flight.Departure_Time
    total_minutes = int(diff.total_seconds() // 60)
    flight.duration = f"{total_minutes // 60}h {total_minutes % 60}m"

    # Re-bind the search form with original query values so the back link works
    search_form = FlightSearchForm(initial={
        'departure_airport': request.GET.get('departure_airport'),
        'arrival_airport': request.GET.get('arrival_airport'),
        'departure_date': request.GET.get('departure_date'),
        'travel_class': request.GET.get('travel_class'),
        'passengers': request.GET.get('passengers'),
    })

    return render(request, 'confirm_flight.html', {
        'flight': flight,
        'passengers': passengers,
        'total_price': flight.Price * passengers,
        'form': search_form,
    })

def passenger_input (request):
    flight_id = request.GET.get('flight_id')
    passengers = int(request.GET.get('passengers', 1))

    flight = get_object_or_404(Flight, id=flight_id)

    # Re-bind the search form with original query values so the back link works
    search_form = FlightSearchForm(initial={
        'departure_airport': request.GET.get('departure_airport'),
        'arrival_airport': request.GET.get('arrival_airport'),
        'departure_date': request.GET.get('departure_date'),
        'travel_class': request.GET.get('travel_class'),
        'passengers': request.GET.get('passengers'),
    })

    return render(request, 'passenger_input.html', {
        'flight': flight,
        'passengers': passengers,
        'total_price': flight.Price * passengers,
        'form': search_form,
    })