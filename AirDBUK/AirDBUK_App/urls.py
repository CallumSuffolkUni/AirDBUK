from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    # AJAX endpoint for typeahead
    path('ajax/airport-autocomplete/', views.airport_autocomplete, name='airport-autocomplete'),
]