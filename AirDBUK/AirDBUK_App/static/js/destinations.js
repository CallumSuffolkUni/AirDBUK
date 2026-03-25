
function goToFlight(departure, arrival) {
    const homeUrl = window.HOME_URL;

    const params = new URLSearchParams({
        departure_airport: departure,
        arrival_airport: arrival,
    });

    window.location.href = homeUrl + "?" + params.toString();
}
