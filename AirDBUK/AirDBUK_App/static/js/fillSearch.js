function fillSearch(departureId, arrivalId, travelClass, passengers) {
    document.querySelector('[name="departure_airport"]').value = departureId;
    document.querySelector('[name="arrival_airport"]').value = arrivalId;
    document.querySelector('[name="travel_class"]').value = travelClass;
    document.querySelector('[name="passengers"]').value = passengers;
}
