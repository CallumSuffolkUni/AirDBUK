from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from .forms import RegisterUserForm, LoginForm
from AirDBUK_App.models import Booking, Passenger, Booking_Passenger, Flight
from AirDBUK_App.forms import AddPassengerDetails
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.forms import formset_factory

# Create your views here.

def login_user(request):
    if request.method == "POST":
        form = LoginForm(request=request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
        else:
            messages.success(request, ("There Was An Error Logging In, Try Again..."))
    else:
        form = LoginForm(request=request)
    
    return render(request, 'authenticate/login.html', {'form': form})

def logout_user(request):
    logout(request)
    messages.success(request, ("You Have Been Logged Out!"))
    return redirect('home')

def register_user(request):
    if request.method == "POST":
        form = RegisterUserForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']
            user = authenticate(username=username, password=password)
            login(request, user)
            messages.success(request, ("Registration Successful"))
            return redirect('dashboard')
    else:
        form = RegisterUserForm()

    return render(request, 'authenticate/register_user.html', {
        'form':form,
    })

def dashboard(request):
    context = {}

    if request.user.is_superuser:
        context['all_users'] = User.objects.all().order_by('date_joined')

        query = request.GET.get('flight_query', '').strip()
        context['flight_query'] = query

        if query:
            context['flight_results'] = Flight.objects.filter(
                Flight_Number__icontains=query
            ).select_related('Departure_Airport', 'Arrival_Airport').order_by('Departure_Time')
        else:
            context['flight_results'] = None

    else:
        context['bookings'] = Booking.objects.filter(
            user=request.user
        ).select_related(
            'Flight_ID__Departure_Airport',
            'Flight_ID__Arrival_Airport'
        ).order_by('-Booking_Date')

    return render(request, 'authenticate/dashboard.html', context)


def user_bookings(request, user_id):
    if not request.user.is_superuser:
        raise PermissionDenied

    target_user = get_object_or_404(User, id=user_id)
    bookings = Booking.objects.filter(user=target_user).select_related(
        'Flight_ID__Departure_Airport',
        'Flight_ID__Arrival_Airport'
    ).order_by('-Booking_Date')

    return render(request, 'authenticate/user_bookings.html', {'target_user': target_user, 'bookings': bookings})


def delete_user(request, user_id):
    if not request.user.is_superuser:
        raise PermissionDenied

    target_user = get_object_or_404(User, id=user_id)

    if target_user == request.user:
        messages.error(request, "You cannot delete your own superuser account.")
        return redirect('dashboard')

    # Cancel existing bookings before delete (request asks for cancel any bookings)
    user_bookings = Booking.objects.filter(user=target_user)
    for booking in user_bookings:
        booking.Status = 'Cancelled'
        booking.save()

    target_user.delete()
    messages.success(request, "User and their bookings have been deleted/cancelled successfully.")
    return redirect('dashboard')


def view_bookings(request, booking_id):
    if request.user.is_superuser:
        booking = get_object_or_404(Booking, id=booking_id)
    else:
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    # Get passengers for this booking
    booking_passengers = Booking_Passenger.objects.filter(Booking_ID=booking).select_related('Passenger_ID')
    passengers = [bp.Passenger_ID for bp in booking_passengers]
    
    PassengerFormSet = formset_factory(AddPassengerDetails, extra=0, can_delete=True)  # No extra forms, allow deleting

    if request.method == "POST":
        formset = PassengerFormSet(request.POST)
        if formset.is_valid():
            for i, form in enumerate(formset):
                if form.cleaned_data.get('DELETE', False):
                    if i < len(passengers):
                        passenger = passengers[i]
                        Booking_Passenger.objects.filter(Booking_ID=booking, Passenger_ID=passenger).delete()
                elif form.cleaned_data:
                    if i < len(passengers):
                        passenger = passengers[i]
                        passenger.First_Name = form.cleaned_data['first_name']
                        passenger.Last_Name = form.cleaned_data['last_name']
                        passenger.DOB = form.cleaned_data['dob']
                        passenger.save()
                    else:
                        passenger = Passenger.objects.create(
                            First_Name=form.cleaned_data['first_name'],
                            Last_Name=form.cleaned_data['last_name'],
                            DOB=form.cleaned_data['dob'],
                            user=booking.user if booking.user else request.user
                        )
                        Booking_Passenger.objects.create(
                            Booking_ID=booking,
                            Passenger_ID=passenger
                        )
            # Update the total price based on current passengers
            current_passengers = Booking_Passenger.objects.filter(Booking_ID=booking)
            booking.Total_Price = len(current_passengers) * booking.Flight_ID.Price
            booking.save()
            messages.success(request, "Passenger details updated successfully.")
            return redirect('dashboard')
    else:
        initial_data = []
        for passenger in passengers:
            initial_data.append({
                'first_name': passenger.First_Name,
                'last_name': passenger.Last_Name,
                'dob': passenger.DOB,
            })
        formset = PassengerFormSet(initial=initial_data)
    
    return render(request, 'authenticate/view_bookings.html', {'formset': formset, 'booking': booking, 'passengers': passengers})


def cancel_flight(request, flight_id):
    if not request.user.is_superuser:
        raise PermissionDenied

    flight = get_object_or_404(Flight, id=flight_id)
    flight.Status = 'Cancelled'
    flight.save()
    messages.success(request, f"Flight {flight.Flight_Number} cancelled successfully.")

    query = request.GET.get('flight_query', '')
    if query:
        return redirect(f"{reverse('dashboard')}?flight_query={query}")
    return redirect('dashboard')


def cancel_booking(request, booking_id):
    if request.user.is_superuser:
        booking = get_object_or_404(Booking, id=booking_id)
    else:
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    booking.Status = 'Cancelled'
    booking.save()
    messages.success(request, "Booking cancelled successfully.")
    return redirect('dashboard')