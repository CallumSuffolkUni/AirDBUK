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
   python manage.py populate_flights --clear      # wipe existing flights first

WHAT THIS GENERATES:
- Hub model: 10 major UK airports fly to all others.
  30 smaller/regional airports only fly to/from the 10 hubs.
- 1 flight per route every 7 days (weekly cadence).
- Each flight produces 3 rows: Economy, Business, First Class
  (same Flight_Number, same times — only Travel_Class differs).
- Flights cover the next ~3 months from tomorrow.
- Target: ~26,910 rows — safely under the 27,000 CleverCloud cap.

ROW MATHS:
  Hub↔Hub routes   : 10 × 9         =    90
  Hub↔Small routes : 10 × 30 × 2   =   600
  Total routes                      =   690
  Flights per route (92 days ÷ 7)   =    13
  Total flights    690 × 13         = 8,970
  Total rows       8,970 × 3        = 26,910
"""

import random
from collections import defaultdict
from datetime import date, timedelta, datetime, time

from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone

from AirDBUK_App.models import Airport, Flight   # ← change app name if needed


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

AIRLINE_PREFIX = "AD"   # AirDBUK — base prefix. Final codes: AD1042E / AD1042B / AD1042F

# (class_name, flight_number_suffix)
TRAVEL_CLASSES = [
    ("Economy",    "E"),
    ("Business",   "B"),
    ("First Class","F"),
]

# How many days apart each route operates (weekly cadence).
FREQUENCY_DAYS = 7

# How many days ahead to generate flights for (~3 months).
DAYS_AHEAD = 92

# Departure window: flights spread between 06:00 and 22:00.
WINDOW_START_HOUR = 6
WINDOW_START_MIN  = 0
SLOT_GAP_MINUTES  = 15   # 15-min gaps — with max ~39 routes/airport/day this is ample

# These 10 airports are designated hubs. They fly to ALL other airports.
# All other airports only fly to/from these hubs — never small-to-small.
HUB_IATA_CODES = {
    "LHR",  # Heathrow          — UK primary hub
    "LGW",  # Gatwick           — Major London secondary
    "MAN",  # Manchester        — Northern England hub
    "BHX",  # Birmingham        — Midlands hub
    "EDI",  # Edinburgh         — Scottish central hub
    "GLA",  # Glasgow           — Scottish west hub
    "ABZ",  # Aberdeen          — Scottish north hub
    "BFS",  # Belfast Intl      — Northern Ireland hub
    "NCL",  # Newcastle         — North East hub
    "BRS",  # Bristol           — South West hub
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_base_number(used: set) -> str:
    """
    Generate a unique base code: AD + 4 digits (e.g. AD1042).
    The 3 class rows append E / B / F → AD1042E, AD1042B, AD1042F.
    Each of those 7-char strings is globally unique across the whole table.
    NOTE: Flight_Number field must have max_length >= 7 in your model.
    """
    while True:
        number = random.randint(1000, 9999)
        base = f"{AIRLINE_PREFIX}{number}"
        variants = [base + suffix for _, suffix in TRAVEL_CLASSES]
        if not any(v in used for v in variants):
            for v in variants:
                used.add(v)
            return base


def estimate_duration_minutes(dep_id: int, arr_id: int) -> int:
    """
    Approximate flight time for a UK domestic route.
    Uses airport ID difference as a rough proxy for distance.
    Range: 45 min (short hop) → 110 min (e.g. London → Shetland/Orkney).
    """
    diff = abs(dep_id - arr_id)
    return max(45, min(110, 45 + diff))


def build_routes(airports: list) -> list:
    """
    Build the list of (departure, arrival) airport pairs using the hub model:
      - Hub → Hub  : every hub flies to every other hub (both directions).
      - Hub → Small: every hub flies to every small airport (both directions).
      - Small → Small: NOT allowed — unrealistic and would exceed the row cap.

    Returns a list of (dep_airport, arr_airport) tuples.
    """
    hubs   = [a for a in airports if a.IATA_Code in HUB_IATA_CODES]
    smalls = [a for a in airports if a.IATA_Code not in HUB_IATA_CODES]

    routes = []

    # Hub ↔ Hub (both directions)
    for dep in hubs:
        for arr in hubs:
            if dep.id != arr.id:
                routes.append((dep, arr))

    # Hub ↔ Small (both directions)
    for hub in hubs:
        for small in smalls:
            routes.append((hub, small))
            routes.append((small, hub))

    return routes


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = (
        "Populate Flight table with a hub-and-spoke model. "
        "Weekly flights per route, 3 class rows per flight, ~3 months ahead. "
        "Targets ~26,910 rows — safely under the 27,000 CleverCloud cap."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear", action="store_true",
            help="Delete all existing Flight records before populating."
        )

    def handle(self, *args, **options):
        cursor = connection.cursor()
        flight_table = Flight._meta.db_table

        try:
            # ── Optional clear ────────────────────────────────────────────
            if options["clear"]:
                cursor.execute(f"DELETE FROM {flight_table}")
                connection.commit()
                self.stdout.write(self.style.WARNING("Deleted all existing flights."))

            # ── Load airports ─────────────────────────────────────────────
            airports = list(Airport.objects.order_by("id"))

            if not airports:
                self.stderr.write("No airports found — populate the Airport table first.")
                return

            hubs   = [a for a in airports if a.IATA_Code in HUB_IATA_CODES]
            smalls = [a for a in airports if a.IATA_Code not in HUB_IATA_CODES]

            self.stdout.write(
                f"\nAirports loaded : {len(airports)} total "
                f"({len(hubs)} hubs, {len(smalls)} regional)\n"
            )

            # Warn if any hub IATA code wasn't found in the DB
            found_iata = {a.IATA_Code for a in airports}
            missing = HUB_IATA_CODES - found_iata
            if missing:
                self.stdout.write(
                    self.style.WARNING(f"  Warning: hub IATA codes not found in DB: {missing}")
                )

            # ── Build routes ──────────────────────────────────────────────
            routes = build_routes(airports)
            random.shuffle(routes)

            start_date = date.today() + timedelta(days=1)   # never book today/past
            end_date   = start_date + timedelta(days=DAYS_AHEAD)

            # Projected totals for the summary banner
            flights_per_route = DAYS_AHEAD // FREQUENCY_DAYS
            projected_rows    = len(routes) * flights_per_route * len(TRAVEL_CLASSES)

            self.stdout.write(
                f"Routes          : {len(routes):,}\n"
                f"Frequency       : every {FREQUENCY_DAYS} days\n"
                f"Date range      : {start_date} → {end_date} ({DAYS_AHEAD} days)\n"
                f"Projected rows  : ~{projected_rows:,} (cap: 27,000)\n"
            )

            # ── Existing flight numbers (avoid unique-constraint clashes) ─
            cursor.execute(f"SELECT Flight_Number FROM {flight_table}")
            used_flight_numbers: set = set(row[0] for row in cursor.fetchall())

            # ── Generate one flight per route per week ────────────────────
            #
            # For each route, pick a random start offset within the first
            # FREQUENCY_DAYS window, then step forward weekly. This spreads
            # departures across all 7 days so no single day is overwhelmed.
            #
            # Per-airport, per-day slot counters ensure no two flights share
            # an exact departure time from the same airport on the same day.

            day_dep_counter: dict = defaultdict(lambda: defaultdict(int))
            day_arr_used: dict    = defaultdict(lambda: defaultdict(set))

            flights_data = []

            for dep_airport, arr_airport in routes:

                # Spread first departure randomly across the first week
                first_offset = random.randint(0, FREQUENCY_DAYS - 1)
                current_date = start_date + timedelta(days=first_offset)

                while current_date < end_date:

                    # ── Departure time ────────────────────────────────────
                    slot_idx       = day_dep_counter[dep_airport.id][current_date]
                    total_dep_mins = (
                        WINDOW_START_HOUR * 60
                        + WINDOW_START_MIN
                        + slot_idx * SLOT_GAP_MINUTES
                    )

                    # Safety valve: clamp to within 06:00–21:59
                    # (shouldn't fire with 15-min gaps and ≤39 routes/day,
                    # but protects against edge cases)
                    if total_dep_mins >= 22 * 60:
                        total_dep_mins = WINDOW_START_HOUR * 60 + (slot_idx % 64) * SLOT_GAP_MINUTES

                    dep_hour = (total_dep_mins // 60) % 24
                    dep_min  =  total_dep_mins % 60
                    dep_dt   = timezone.make_aware(
                        datetime.combine(current_date, time(dep_hour, dep_min))
                    )
                    day_dep_counter[dep_airport.id][current_date] += 1

                    # ── Arrival time ──────────────────────────────────────
                    duration = estimate_duration_minutes(dep_airport.id, arr_airport.id)
                    arr_dt   = dep_dt + timedelta(minutes=duration)

                    # Nudge forward 1 min until the arrival slot is free
                    while arr_dt in day_arr_used[arr_airport.id][current_date]:
                        arr_dt += timedelta(minutes=1)
                    day_arr_used[arr_airport.id][current_date].add(arr_dt)

                    # ── Flight number + 3 class rows ──────────────────────
                    base_fn = make_base_number(used_flight_numbers)

                    for travel_class, suffix in TRAVEL_CLASSES:
                        flights_data.append((
                            base_fn + suffix,      # Flight_Number  e.g. AD1042E
                            dep_dt,                # Departure_Time
                            arr_dt,                # Arrival_Time
                            "Scheduled",           # Status
                            travel_class,          # Travel_Class
                            dep_airport.id,        # Departure_Airport_id
                            arr_airport.id,        # Arrival_Airport_id
                        ))

                    current_date += timedelta(days=FREQUENCY_DAYS)

            # ── Bulk insert in batches of 5,000 ──────────────────────────
            if flights_data:
                sql = f"""
                    INSERT INTO {flight_table}
                    (Flight_Number, Departure_Time, Arrival_Time, Status, Travel_Class,
                     Departure_Airport_id, Arrival_Airport_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                batch_size = 5000
                for i in range(0, len(flights_data), batch_size):
                    cursor.executemany(sql, flights_data[i:i + batch_size])
                    connection.commit()
                    self.stdout.write(
                        f"  Inserted rows up to {min(i + batch_size, len(flights_data)):,} …"
                    )

            # ── Final count ───────────────────────────────────────────────
            cursor.execute(f"SELECT COUNT(*) FROM {flight_table}")
            total_count = cursor.fetchone()[0]

            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅  Done!\n"
                    f"    Records inserted : {len(flights_data):,}\n"
                    f"    Total in DB now  : {total_count:,}\n"
                    f"    Bookable from    : {start_date} → {end_date}\n"
                    f"    Row cap usage    : {total_count:,} / 27,000 "
                    f"({round(total_count / 27000 * 100)}%)"
                )
            )

        finally:
            cursor.close()