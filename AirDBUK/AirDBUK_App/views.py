from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from .forms import FlightSearchForm
from .models import *

# Create your views here.

def airport_autocomplete(request):
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
        """Try to resolve a displayed airport string back to an Airport instance."""
        if not value:
            return None
        # try to extract IATA code from parentheses at end
        import re
        m = re.search(r"\((\w{3})\)$", value)
        if m:
            code = m.group(1)
            return Airport.objects.filter(IATA_Code__iexact=code).first()
        # fallback: try matching city or name
        return Airport.objects.filter(
            Q(City__iexact=value) | Q(Name__iexact=value) | Q(IATA_Code__iexact=value)
        ).first()

    from_airport = lookup_airport(from_airport_str)
    to_airport = lookup_airport(to_airport_str)

    return Flight.objects.filter(
        Departure_Airport=from_airport,
        Arrival_Airport=to_airport,
        Departure_Time__date=departure_date,
        Travel_Class=travel_class
    )


def home(request):
    """Render landing page with an empty search form."""
    form = FlightSearchForm()
    return render(request, 'home.html', {'form': form})


def search_results(request):
    """Display flights matching query parameters from the search form."""
    form = FlightSearchForm(request.GET or None)
    flights = _perform_search(form)
    return render(request, 'search_results.html', {'form': form, 'flights': flights})
