import csv
import random
from datetime import datetime, timedelta

AIRPORTS = list(range(1, 41))
CLASSES = [("Economy", "E", 1.0), ("Business", "B", 2.5), ("First Class", "F", 4.0)]

start_date = datetime.now() + timedelta(days=1)

print("Writing CSV...")

with open("flights.csv", "w", newline="") as f:

    writer = csv.writer(f)

    writer.writerow([
        "Flight_Number",
        "Departure_Time",
        "Arrival_Time",
        "Status",
        "Travel_Class",
        "Price",
        "Departure_Airport_id",
        "Arrival_Airport_id"
    ])

    for day in range(90):

        current_day = start_date + timedelta(days=day)

        for dep in AIRPORTS:
            for arr in AIRPORTS:

                if dep == arr:
                    continue

                dep_time = current_day.replace(hour=6) + timedelta(minutes=random.randint(0, 960))
                arr_time = dep_time + timedelta(minutes=random.randint(45, 100))

                base_price = random.randint(50, 300)  # base economy price
                base = random.randint(1000, 9999)

                for c, suffix, multiplier in CLASSES:

                    writer.writerow([
                        f"AD{base}{suffix}",
                        dep_time.strftime("%Y-%m-%d %H:%M:%S"),
                        arr_time.strftime("%Y-%m-%d %H:%M:%S"),
                        "Scheduled",
                        c,
                        round(base_price * multiplier, 2),  # Price
                        dep,
                        arr
                    ])

print("Done.")