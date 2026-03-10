from django.shortcuts import render, redirect, get_object_or_404
from django.template import loaders
#from .forms import addBooking, addFlight
from .models import *

# Create your views here.
def home(request):
    return render(request, 'home.html')
