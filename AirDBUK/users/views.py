from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from .forms import RegisterUserForm
from AirDBUK_App.models import Booking, Passenger, Booking_Passenger
from AirDBUK_App.forms import AddPassengerDetails
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.forms import formset_factory

# Create your views here.

def login_user(request):
    if request.method =="POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.success(request, ("There Was An Error Logging In, Try Again..."))
            return redirect('login')
    else:
        return render(request, 'authenticate/login.html', {})

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
    else:
        context['bookings'] = Booking.objects.filter(
            user=request.user
        ).select_related(
            'Flight_ID__Departure_Airport',
            'Flight_ID__Arrival_Airport'
        ).order_by('-Booking_Date')

    return render(request, 'authenticate/dashboard.html', context)

def view_bookings(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    # Get passengers for this booking
    booking_passengers = Booking_Passenger.objects.filter(Booking_ID=booking).select_related('Passenger_ID')
    passengers = [bp.Passenger_ID for bp in booking_passengers]
    
    PassengerFormSet = formset_factory(AddPassengerDetails, extra=1, can_delete=True)  # Allow adding one more and deleting
    
    if request.method == "POST":
        formset = PassengerFormSet(request.POST)
        if formset.is_valid():
            for i, form in enumerate(formset):
                if form.cleaned_data.get('DELETE', False):
                    # Delete the passenger
                    if i < len(passengers):
                        passenger = passengers[i]
                        Booking_Passenger.objects.filter(Booking_ID=booking, Passenger_ID=passenger).delete()
                        # Optionally delete the passenger if not used elsewhere, but for now keep
                elif form.cleaned_data:  # Only if form has data and not deleted
                    if i < len(passengers):
                        # Update existing passenger
                        passenger = passengers[i]
                        passenger.First_Name = form.cleaned_data['first_name']
                        passenger.Last_Name = form.cleaned_data['last_name']
                        passenger.DOB = form.cleaned_data['dob']
                        passenger.save()
                    else:
                        # Create new passenger
                        passenger = Passenger.objects.create(
                            First_Name=form.cleaned_data['first_name'],
                            Last_Name=form.cleaned_data['last_name'],
                            DOB=form.cleaned_data['dob'],
                            user=request.user
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