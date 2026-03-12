"""
import_flights.py
-----------------
Inserts flights.csv into the __AirDBUK_App_flight__ table on Clever Cloud MySQL.

Requirements:
    pip install pymysql

Usage:
    python import_flights.py --csv "C:\\path\\to\\flights.csv"
"""

import argparse
import csv
import os
import sys
import time
import pymysql

DB_CONFIG = {
    "host":            "bhqxgza1j25vgtvphhdc-mysql.services.clever-cloud.com",
    "port":            3306,
    "db":              "bhqxgza1j25vgtvphhdc",
    "user":            "utbva8pchvvqbziv",
    "password":        "hwsp5fqTWunm2rNJj5Rw",
    "connect_timeout": 30,
    "autocommit":      False,
}

TABLE      = "AirDBUK_App_flight"
BATCH_SIZE = 5_000

INSERT_SQL = f"""
    INSERT IGNORE INTO `{TABLE}`
        (Flight_Number, Departure_Airport_id, Arrival_Airport_id,
         Departure_Time, Arrival_Time, Status, Travel_Class)
    VALUES
        (%s, %s, %s, %s, %s, %s, %s)
"""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="Full path to flights.csv")
    args = parser.parse_args()
    csv_path = args.csv

    print(f"CSV path   : {csv_path}")
    if not os.path.exists(csv_path):
        print(f"ERROR: File not found: {csv_path}")
        sys.exit(1)
    print(f"File found : YES ({os.path.getsize(csv_path):,} bytes)")

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        total = sum(1 for _ in f) - 1
    print(f"Rows       : {total:,}\n")

    print("Connecting to database ...")
    try:
        conn = pymysql.connect(**DB_CONFIG)
        print("Connected!\n")
    except Exception as e:
        print(f"Connection failed: {type(e).__name__}: {e}")
        sys.exit(1)

    cursor = conn.cursor()
    inserted = 0
    batch = []
    start_time = time.time()

    try:
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            print(f"Columns detected: {reader.fieldnames}\n")

            for row in reader:
                batch.append((
                    row["Flight_Number"],
                    int(row["Departure_Airport_id"]),
                    int(row["Arrival_Airport_id"]),
                    row["Departure_Time"],
                    row["Arrival_Time"],
                    row["Status"],
                    row["Travel_Class"],
                ))

                if len(batch) >= BATCH_SIZE:
                    cursor.executemany(INSERT_SQL, batch)
                    conn.commit()
                    inserted += len(batch)
                    batch = []
                    pct = inserted / total * 100
                    elapsed = time.time() - start_time
                    rate = inserted / elapsed if elapsed else 0
                    print(f"  {inserted:>8,} / {total:,}  ({pct:5.1f}%)  {rate:,.0f} rows/s")

            if batch:
                cursor.executemany(INSERT_SQL, batch)
                conn.commit()
                inserted += len(batch)

        elapsed = time.time() - start_time
        print(f"\nDone! {inserted:,} rows inserted in {elapsed:.1f}s ({inserted/elapsed:,.0f} rows/s).")

    except KeyboardInterrupt:
        print("\nInterrupted - rolling back.")
        conn.rollback()
    except Exception as e:
        print(f"\nError ({type(e).__name__}): {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()
        print("Connection closed.")

if __name__ == "__main__":
    main()