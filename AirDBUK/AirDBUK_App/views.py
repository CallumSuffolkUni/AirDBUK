import calendar
import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from .forms import FlightSearchForm, AddPassengerDetails
from .models import *
from django.forms import formset_factory
from users.forms import RegisterUserForm, LoginForm
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone
from decimal import Decimal
from django.core.management import call_command

# Create your views here.


def lookup_airport(value):
    """Convert an airport search string into an Airport instance."""
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


def home(request):
    call_command('update_flight_status')
    initial = {
        'departure_airport': request.GET.get('departure_airport', ''),
        'arrival_airport': request.GET.get('arrival_airport', ''),
    }
    form = FlightSearchForm(initial=initial)
    return render(request, 'home.html', {'form': form})

def confirmation(request):
    return render(request, 'confirmation.html')


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

    from_airport = lookup_airport(from_airport_str)
    to_airport = lookup_airport(to_airport_str)

    return Flight.objects.filter(
        Departure_Airport=from_airport,
        Arrival_Airport=to_airport,
        Departure_Time__date=departure_date,
        Status='Scheduled',
    )

def search_results(request):
    form = FlightSearchForm(request.GET or None)

    flights = _perform_search(form)
    print("FLIGHTS FOUND:", len(flights) if flights else 0)

    # Determine which month to show in the calendar
    today = datetime.date.today()
    selected_date = today
    if form.is_valid():
        selected_date = form.cleaned_data.get('departure_date') or today

    # Support month/year navigation
    calendar_year = int(request.GET.get('calendar_year', selected_date.year))
    calendar_month = int(request.GET.get('calendar_month', selected_date.month))

    # Find all available dates for the selected route / class
    # Done independently of form validity — only needs airport/class params
    available_dates = set()
    from_airport = lookup_airport(request.GET.get('departure_airport'))
    to_airport = lookup_airport(request.GET.get('arrival_airport'))
    travel_class = request.GET.get('travel_class')

    if from_airport and to_airport:
        qs = Flight.objects.filter(
            Departure_Airport=from_airport,
            Arrival_Airport=to_airport,
            Status='Scheduled',
        )
        if travel_class:
            qs = qs.filter(Travel_Class=travel_class)

        available_dates = set(qs.values_list('Departure_Time__date', flat=True))

    # Build a month grid for the calendar
    cal = calendar.Calendar(firstweekday=0)
    calendar_weeks = cal.monthdayscalendar(calendar_year, calendar_month)

    # Calculate previous and next month for navigation
    if calendar_month == 1:
        prev_month = 12
        prev_year = calendar_year - 1
    else:
        prev_month = calendar_month - 1
        prev_year = calendar_year

    if calendar_month == 12:
        next_month = 1
        next_year = calendar_year + 1
    else:
        next_month = calendar_month + 1
        next_year = calendar_year

    available_days = {
        d.day for d in available_dates
        if d.year == calendar_year and d.month == calendar_month
    }
    selected_day = selected_date.day if (selected_date.year == calendar_year and selected_date.month == calendar_month) else None

    # Keep the current query parameters for calendar links
    base_query = {
        'departure_airport': request.GET.get('departure_airport', ''),
        'arrival_airport': request.GET.get('arrival_airport', ''),
        'travel_class': request.GET.get('travel_class', ''),
        'passengers': request.GET.get('passengers', ''),
        'departure_date': request.GET.get('departure_date', ''),
    }

    # Add duration to each flight
    for flight in flights:
        diff = flight.Arrival_Time - flight.Departure_Time
        total_minutes = int(diff.total_seconds() // 60)
        flight.duration = f"{total_minutes // 60}h {total_minutes % 60}m"

    return render(request, 'search_results.html', {
        'form': form,
        'flights': flights,
        'calendar_year': calendar_year,
        'calendar_month': calendar_month,
        'calendar_month_name': calendar.month_name[calendar_month],
        'calendar_weeks': calendar_weeks,
        'available_days': available_days,
        'selected_day': selected_day,
        'base_query': base_query,
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
    })


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

def passenger_input(request):
    flight_id = request.GET.get('flight_id')
    passengers = int(request.GET.get('passengers', 1))
    flight = get_object_or_404(Flight, id=flight_id)

    PassengerFormSet = formset_factory(AddPassengerDetails, extra=passengers)

    formset = PassengerFormSet(prefix="passengers")
    form_a = LoginForm(prefix="login")
    form_b = RegisterUserForm(prefix="register")

    if request.method == "POST":
        action = request.POST.get("action")
        formset = PassengerFormSet(request.POST, prefix="passengers")

        # --- Already logged in ---
        if request.user.is_authenticated:
            if formset.is_valid():
                passenger_data = []
                for form in formset:
                    cd = form.cleaned_data
                    passenger_data.append({
                        'First_Name': cd.get('first_name', ''),
                        'Last_Name': cd.get('last_name', ''),
                        'DOB': cd['dob'].strftime('%Y-%m-%d') if cd.get('dob') else '',
                    })
                request.session['passenger_data'] = passenger_data
                request.session['total_price'] = str(flight.Price * passengers)
                return redirect(f"/payment/?flight_id={flight_id}&passengers={passengers}")

        # --- Not logged in: chose to sign in ---
        elif action == "login":
            form_a = LoginForm(request, data=request.POST)
            if form_a.is_valid() and formset.is_valid():
                user = form_a.get_user()
                login(request, user)
                passenger_data = []
                for form in formset:
                    cd = form.cleaned_data
                    passenger_data.append({
                        'First_Name': cd.get('first_name', ''),
                        'Last_Name': cd.get('last_name', ''),
                        'DOB': cd['dob'].strftime('%Y-%m-%d') if cd.get('dob') else '',
                    })
                request.session['passenger_data'] = passenger_data
                request.session['total_price'] = str(flight.Price * passengers)
                return redirect(f"/payment/?flight_id={flight_id}&passengers={passengers}")

        # --- Not logged in: chose to register ---
        elif action == "register":
            form_b = RegisterUserForm(request.POST, prefix="register")
            if formset.is_valid() and form_b.is_valid():
                user = form_b.save()
                user = authenticate(
                    username = form_b.cleaned_data['username'],
                    password = form_b.cleaned_data['password1']
                )
                login(request, user)
                passenger_data = []
                for form in formset:
                    cd = form.cleaned_data
                    passenger_data.append({
                        'First_Name': cd.get('first_name', ''),
                        'Last_Name': cd.get('last_name', ''),
                        'DOB': cd['dob'].strftime('%Y-%m-%d') if cd.get('dob') else '',
                    })
                request.session['passenger_data'] = passenger_data
                request.session['total_price'] = str(flight.Price * passengers)
                messages.success(request, "Account created successfully!")
                return redirect(f"/payment/?flight_id={flight_id}&passengers={passengers}")

    return render(request, 'passenger_input.html', {
        'flight': flight,
        'passengers': passengers,
        'total_price': flight.Price * passengers,
        'formset': formset,
        'form_b': form_b,
        'form_a': form_a,
    })

def payment(request):
    flight_id = request.GET.get('flight_id')
    passengers = int(request.GET.get('passengers', 1))

    passenger_data = request.session.get('passenger_data')
    
    total_price = request.session.get('total_price')
    flight = get_object_or_404(Flight, id=flight_id)

    if request.method == "POST":
        booking = Booking.objects.create(
            Booking_Date = timezone.now(),
            Status = 'Booked',
            Total_Price = Decimal(total_price),
            Flight_ID = flight,
            user = request.user,
        )

        for p in passenger_data:
            passenger = Passenger.objects.create(
                First_Name = p['First_Name'],
                Last_Name = p['Last_Name'],
                DOB = datetime.datetime.strptime(p['DOB'], '%Y-%m-%d').date(),
                user = request.user,
            )

            Booking_Passenger.objects.create(
            Booking_ID = booking,
            Passenger_ID = passenger,
            )

        del request.session['passenger_data']
        del request.session['total_price']

        return redirect('confirmation')

    return render(request, 'payment.html', {
        'flight': flight,
        'passengers': passengers,
        'passenger_data': passenger_data,
        'total_price': total_price,
    })

def destinations(request):
    return render(request, 'destination.html')