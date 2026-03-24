"""
generate_flights.py — AirDBUK flight CSV generator

Run locally with plain Python (no Django needed):
    python generate_flights.py

Outputs:
    flights.csv  — ready to import directly into CleverCloud via the DB console

WHAT THIS GENERATES:
  Hub model: 10 major airports fly to all 39 others (both directions).
  30 regional/island airports only fly to/from the 10 hubs.
  1 flight per route every 7 days over 92 days (~3 months).
  3 rows per flight (Economy / Business / First Class) — same dep/arr time.

ROW MATHS:
  Hub↔Hub routes   : 10 × 9       =    90
  Hub↔Small routes : 10 × 30 × 2  =   600
  Total routes                     =   690
  Flights per route (92 days ÷ 7)  =    13
  Total flights    690 × 13        = 8,970
  Total rows       8,970 × 3       = 26,910 
"""

import csv
import random
from collections import defaultdict
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

FREQUENCY_DAYS   = 7     # one flight per route per week
DAYS_AHEAD       = 92    # ~3 months
SLOT_GAP_MINUTES = 15    # min gap between departures from same airport on same day
WINDOW_START     = 6     # earliest departure hour (06:00)
WINDOW_END       = 22    # latest departure hour  (22:00)

# Airport IDs matching your DB (1–40 as seeded)
ALL_AIRPORT_IDS = list(range(1, 41))

# Hub airport IDs — cross-referenced from your airport table
# ID : IATA  : Name
#  1 : LHR   : Heathrow
#  2 : LGW   : Gatwick
#  7 : MAN   : Manchester
#  8 : BHX   : Birmingham
# 13 : EDI   : Edinburgh
# 14 : GLA   : Glasgow
# 16 : ABZ   : Aberdeen
# 18 : BFS   : Belfast International
# 12 : NCL   : Newcastle
#  9 : BRS   : Bristol
HUB_IDS = {1, 2, 7, 8, 9, 12, 13, 14, 16, 18}

SMALL_IDS = set(ALL_AIRPORT_IDS) - HUB_IDS

# (class_name, flight_number_suffix, price_multiplier)
CLASSES = [
    ("Economy",    "E", 1.0),
    ("Business",   "B", 2.5),
    ("First Class","F", 4.0),
]

OUTPUT_FILE = "flights.csv"

# ---------------------------------------------------------------------------
# Build routes (hub-and-spoke)
# ---------------------------------------------------------------------------

routes = []

# Hub ↔ Hub (both directions)
hub_list = sorted(HUB_IDS)
for dep in hub_list:
    for arr in hub_list:
        if dep != arr:
            routes.append((dep, arr))

# Hub ↔ Small (both directions)
small_list = sorted(SMALL_IDS)
for hub in hub_list:
    for small in small_list:
        routes.append((hub, small))
        routes.append((small, hub))

random.shuffle(routes)

# ---------------------------------------------------------------------------
# Generate flights
# ---------------------------------------------------------------------------

start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
end_date   = start_date + timedelta(days=DAYS_AHEAD)

used_flight_numbers = set()

# Track slots per (airport_id, date_str) to avoid duplicate departure times
dep_slot_counter = defaultdict(int)       # key: (airport_id, date_str)
arr_times_used   = defaultdict(set)       # key: (airport_id, date_str)


def make_flight_number():
    """Return a unique base like AD1042; reserves AD1042E/B/F together."""
    while True:
        base = f"AD{random.randint(1000, 9999)}"
        variants = [base + s for _, s, _ in CLASSES]
        if not any(v in used_flight_numbers for v in variants):
            for v in variants:
                used_flight_numbers.add(v)
            return base


def duration_minutes(dep_id: int, arr_id: int) -> int:
    """Rough UK domestic flight time based on airport ID gap (proxy for distance)."""
    return max(45, min(110, 45 + abs(dep_id - arr_id)))


print(f"Routes      : {len(routes):,}")
print(f"Date range  : {start_date.date()} → {end_date.date()} ({DAYS_AHEAD} days)")
print(f"Projected   : ~{len(routes) * (DAYS_AHEAD // FREQUENCY_DAYS) * 3:,} rows")
print(f"Writing {OUTPUT_FILE} …\n")

rows_written = 0

with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "Flight_Number",
        "Departure_Time",
        "Arrival_Time",
        "Status",
        "Travel_Class",
        "Price",
        "Departure_Airport_id",
        "Arrival_Airport_id",
    ])

    for dep_id, arr_id in routes:

        # Spread each route's first flight randomly within the first week
        first_offset = random.randint(0, FREQUENCY_DAYS - 1)
        current = start_date + timedelta(days=first_offset)

        while current < end_date:

            date_str = current.strftime("%Y-%m-%d")

            # ── Departure time ───────────────────────────────────────────
            slot_key  = (dep_id, date_str)
            slot_idx  = dep_slot_counter[slot_key]
            dep_mins  = WINDOW_START * 60 + slot_idx * SLOT_GAP_MINUTES

            # Safety clamp — should not trigger with 15-min gaps & ≤39 slots/day
            if dep_mins >= WINDOW_END * 60:
                dep_mins = WINDOW_START * 60 + (slot_idx % 64) * SLOT_GAP_MINUTES

            dep_time = current + timedelta(minutes=dep_mins)
            dep_slot_counter[slot_key] += 1

            # ── Arrival time ─────────────────────────────────────────────
            arr_time = dep_time + timedelta(minutes=duration_minutes(dep_id, arr_id))

            arr_key = (arr_id, date_str)
            while arr_time in arr_times_used[arr_key]:
                arr_time += timedelta(minutes=1)
            arr_times_used[arr_key].add(arr_time)

            # ── Base price (Economy) — random £50–£300 ───────────────────
            base_price = random.randint(50, 300)

            # ── Write one row per travel class ───────────────────────────
            base_fn = make_flight_number()

            for cls_name, suffix, multiplier in CLASSES:
                writer.writerow([
                    base_fn + suffix,                               # Flight_Number
                    dep_time.strftime("%Y-%m-%d %H:%M:%S"),         # Departure_Time
                    arr_time.strftime("%Y-%m-%d %H:%M:%S"),         # Arrival_Time
                    "Scheduled",                                    # Status
                    cls_name,                                       # Travel_Class
                    round(base_price * multiplier, 2),              # Price
                    dep_id,                                         # Departure_Airport_id
                    arr_id,                                         # Arrival_Airport_id
                ])
                rows_written += 1

            current += timedelta(days=FREQUENCY_DAYS)

print(f"Done. {rows_written:,} rows written to {OUTPUT_FILE}")
print(f"Cap usage: {rows_written:,} / 27,000 ({round(rows_written / 27000 * 100)}%)")