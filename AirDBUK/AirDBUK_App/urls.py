from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('search/', views.search_results, name='search_results'),
    path('confirm-flight/', views.confirm_flight, name='confirm_flight'),
    # AJAX endpoint for typeahead
    path('ajax/airport-autocomplete/', views.airport_autocomplete, name='airport-autocomplete'),
]