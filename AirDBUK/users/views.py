from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from .forms import RegisterUserForm
from AirDBUK_App.models import Booking
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied

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