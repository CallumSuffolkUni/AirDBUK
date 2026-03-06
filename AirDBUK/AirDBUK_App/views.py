from django.shortcuts import render
from django.shortcuts import HttpResponse

# Create your views here.
def index(request):
    return render(request, 'base.html')

def about(request):
    return HttpResponse('Welcome to About Page')