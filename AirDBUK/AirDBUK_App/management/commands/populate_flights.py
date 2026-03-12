"""
Django Management Command: populate_flights.py

SETUP INSTRUCTIONS:
1. Create the directory structure in your Django app:
   AirDBUK_App/
   └── management/
       ├── __init__.py
       └── commands/
           ├── __init__.py
           └── populate_flights.py

2. Place this file at:
   AirDBUK_App/management/commands/populate_flights.py

3. Run with:
   python manage.py populate_flights

   Optional flags:
   python manage.py populate_flights --days 90        # default: 90 days
   python manage.py populate_flights --clear          # wipe existing flights first
   python manage.py populate_flights --days 30 --clear

WHAT THIS GENERATES:
- 1 flight per route per day  (LHR→MAN is one flight; MAN→LHR is a separate flight)
- Each flight produces 3 rows: Economy, Business, First Class
  (same Flight_Number, same times — only Travel_Class differs)
- No two flights depart the same airport at the same time
- No two flights arrive at the same airport at the same time
- Flights start from TOMORROW — users cannot book today or any past date
- 40 airports × 39 destinations = 1,560 routes/day
  × 3 classes × 90 days ≈ 421,200 total records

"""
from django.db import connection
from django.db import transaction
from django.db import close_old_connections
import random
from datetime import date, timedelta, datetime, time
from django.core.management.base import BaseCommand
from django.utils import timezone
from AirDBUK_App.models import Airport, Flight   # ← change app name if needed


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

AIRLINE_PREFIX = "AD"   # AirDBUK — base prefix. Final numbers: AD1042E / AD1042B / AD1042F

# (class_name, flight_number_suffix)
TRAVEL_CLASSES = [
    ("Economy",    "E"),
    ("Business",   "B"),
    ("First Class","F"),
]

# Flights spread between 06:00 and 22:00 (960-min window).
# With 39 routes per departure airport and 6-min gaps, we need 39 × 6 = 234 min,
# well within the 960-min window — so no airport ever runs out of slots.
WINDOW_START_HOUR = 6
WINDOW_START_MIN  = 0
SLOT_GAP_MINUTES  = 6


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_base_number(used: set) -> str:
    """
    Generate a unique base code: AD + 4 digits (e.g. AD1042).
    The 3 class rows will append E / B / F giving AD1042E, AD1042B, AD1042F.
    Each of those 7-char strings is globally unique.
    NOTE: update Flight_Number max_length to 7 in your model.
    """
    while True:
        number = random.randint(1000, 9999)
        base = f"{AIRLINE_PREFIX}{number}"          # e.g. AD1042
        # Reserve all three suffixed variants at once
        variants = [base + "E", base + "B", base + "F"]
        if not any(v in used for v in variants):
            for v in variants:
                used.add(v)
            return base


def estimate_duration_minutes(dep_id: int, arr_id: int) -> int:
    """
    Approximate flight time for a UK domestic route.
    Uses airport ID difference as a rough proxy for distance.
    Range: 45 min (short hop) → 100 min (e.g. London → Shetland).
    """
    diff = abs(dep_id - arr_id)
    return max(45, min(100, 45 + diff))


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = (
        "Populate Flight table: 1 flight per route per day for N days, "
        "3 class rows per flight, all dated from tomorrow onwards."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--days", type=int, default=90,
            help="Days to populate from tomorrow (default: 90)"
        )
        parser.add_argument(
            "--clear", action="store_true",
            help="Delete all existing Flight records before populating"
        )

    def handle(self, *args, **options):

        # ── Optional clear ───────────────────────────────────────────────
        if options["clear"]:
            deleted, _ = Flight.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} existing flights."))

        # ── Load airports ────────────────────────────────────────────────
        airports = list(Airport.objects.order_by("id"))
        if not airports:
            self.stderr.write("No airports found — populate the Airport table first.")
            return

        n_airports = len(airports)
        n_days     = options["days"]

        # Start TOMORROW so today and past dates are never bookable
        start_date = date.today() + timedelta(days=1)

        self.stdout.write(
            f"\nGenerating {n_airports * (n_airports - 1):,} routes/day "
            f"× 3 classes × {n_days} days "
            f"starting {start_date} …\n"
        )

        # Collect flight numbers already in DB to avoid unique-constraint errors
        used_flight_numbers: set = set(
            Flight.objects.values_list("Flight_Number", flat=True)
        )

        total_inserted = 0

        # ── Main loop: one day at a time ─────────────────────────────────
        for day_offset in range(n_days):

            close_old_connections()   # ← important for Clever Cloud
            
            current_day = start_date + timedelta(days=day_offset)
            flights_today = []

            # Per-airport slot counters reset each day
            # departure_slot_counter[airport_id] → how many departures assigned so far
            departure_slot_counter: dict[int, int] = {a.id: 0 for a in airports}

            # Per-airport arrival sets reset each day (to block duplicate arrival times)
            arrival_times_used: dict[int, set] = {a.id: set() for a in airports}

            # Shuffle so no airport always "wins" the earliest morning slot
            routes = [
                (dep, arr)
                for dep in airports
                for arr in airports
                if dep.id != arr.id
            ]
            random.shuffle(routes)

            for dep_airport, arr_airport in routes:

                # ── Departure time ────────────────────────────────────────
                slot_idx       = departure_slot_counter[dep_airport.id]
                total_dep_mins = (
                    WINDOW_START_HOUR * 60
                    + WINDOW_START_MIN
                    + slot_idx * SLOT_GAP_MINUTES
                )
                dep_hour = (total_dep_mins // 60) % 24
                dep_min  =  total_dep_mins % 60
                dep_dt   = timezone.make_aware(
                    datetime.combine(current_day, time(dep_hour, dep_min))
                )
                departure_slot_counter[dep_airport.id] += 1

                # ── Arrival time ──────────────────────────────────────────
                duration = estimate_duration_minutes(dep_airport.id, arr_airport.id)
                arr_dt   = dep_dt + timedelta(minutes=duration)

                # Nudge forward 1 min at a time until the slot is free
                while arr_dt in arrival_times_used[arr_airport.id]:
                    arr_dt += timedelta(minutes=1)
                arrival_times_used[arr_airport.id].add(arr_dt)

                # ── Generate base flight number; each class gets its own suffixed variant ──
                base_fn = make_base_number(used_flight_numbers)

                for travel_class, suffix in TRAVEL_CLASSES:
                    flights_today.append(
                        Flight(
                            Flight_Number=base_fn + suffix,   # e.g. AD1042E
                            Departure_Time=dep_dt,
                            Arrival_Time=arr_dt,
                            Status="Scheduled",
                            Travel_Class=travel_class,
                            Departure_Airport=dep_airport,
                            Arrival_Airport=arr_airport,
                        )
                    )

            # ── Bulk insert for the day ───────────────────────────────────
            with transaction.atomic():
                Flight.objects.bulk_create(flights_today, batch_size=2000)

            total_inserted += len(flights_today)
            self.stdout.write(
                f"  {current_day}  →  {len(flights_today):,} records inserted"
            )

        # ── Summary ──────────────────────────────────────────────────────
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅  Done!\n"
                f"    Records inserted : {total_inserted:,}\n"
                f"    Total in DB now  : {Flight.objects.count():,}\n"
                f"    Bookable from    : {start_date} onwards"
            )
        )