from django.test import TestCase
from django.urls import reverse
from .models import Airport
from .forms import FlightSearchForm


class AirportAutocompleteTests(TestCase):
    def setUp(self):
        # create a couple of airports to search
        Airport.objects.create(City='London', Name='Heathrow', IATA_Code='LHR')
        Airport.objects.create(City='Manchester', Name='Airport', IATA_Code='MAN')

    def test_autocomplete_returns_matches(self):
        url = reverse('airport-autocomplete')
        response = self.client.get(url, {'term': 'Lon'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # should include Heathrow representation string
        self.assertTrue(any('LHR' in s for s in data))

    def test_autocomplete_no_term(self):
        url = reverse('airport-autocomplete')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])


class FlightSearchFormTests(TestCase):
    def test_fields_have_list_attributes(self):
        form = FlightSearchForm()
        self.assertIn('list="departure-list"', str(form['departure_airport']))
        self.assertIn('list="arrival-list"', str(form['arrival_airport']))

