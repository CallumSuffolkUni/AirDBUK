from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from AirDBUK_App.models import Flight


class Command(BaseCommand):
    help = "Updates flight statuses based on current time, and deletes old flights."

    def handle(self, *args, **options):
        now = timezone.now()
        three_days_ago = now - timedelta(days=3)

        # --- 1. Delete flights that landed more than 3 days ago ---
        deleted_qs = Flight.objects.filter(Arrival_Time__lt=three_days_ago)
        deleted_count, _ = deleted_qs.delete()
        self.stdout.write(f"Deleted {deleted_count} old flight(s).")

        # --- 2. Mark as "Landed" if arrival time has passed (within 3 days) ---
        landed_count = Flight.objects.filter(
            Arrival_Time__lte=now,
            Arrival_Time__gte=three_days_ago,
        ).exclude(Status__in=["Landed", "Cancelled"]).update(Status="Landed")
        self.stdout.write(f"Marked {landed_count} flight(s) as Landed.")

        # --- 3. Mark as "Departed" if currently in-flight ---
        departed_count = Flight.objects.filter(
            Departure_Time__lte=now,
            Arrival_Time__gt=now,
        ).exclude(Status__in=["Departed", "Cancelled"]).update(Status="Departed")
        self.stdout.write(f"Marked {departed_count} flight(s) as Departed.")

        self.stdout.write(self.style.SUCCESS("Flight Status update complete."))