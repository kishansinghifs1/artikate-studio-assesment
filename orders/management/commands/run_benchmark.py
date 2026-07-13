import time
from django.core.management.base import BaseCommand
from django.db import connection, reset_queries
from django.contrib.auth.models import User
from orders.models import Tenant, Customer, Order, OrderItem
from orders.managers import bind_tenant


class Command(BaseCommand):
    help = "Seeds 250 orders and prints N+1 vs optimized query counts"

    def handle(self, *args, **options):
        # --- Setup ---
        tenant, _ = Tenant.objects.get_or_create(name="Bench", subdomain="bench")
        user, created = User.objects.get_or_create(username="bench_user")
        if created:
            user.set_password("pass")
            user.save()

        with bind_tenant(tenant):
            OrderItem.objects.all().delete()
            Order.objects.all().delete()
            Customer.objects.all().delete()

            cust = Customer.objects.create(tenant=tenant, name="Alice", email="a@b.com")
            orders = Order.objects.bulk_create(
                [Order(tenant=tenant, user=user, customer=cust) for _ in range(250)]
            )
            OrderItem.objects.bulk_create([
                OrderItem(tenant=tenant, order=o, sku=f"S-{i}-{j}", quantity=1, price=9.99)
                for i, o in enumerate(orders) for j in range(3)
            ])

        self.stdout.write(self.style.SUCCESS("Seeded 250 orders × 3 items"))

        # --- Benchmark: Unoptimized (N+1) ---
        with bind_tenant(tenant):
            reset_queries()
            connection.force_debug_cursor = True

            t0 = time.perf_counter()
            qs = Order.objects.filter(user=user)
            for o in qs:
                _ = o.customer.name
                _ = list(o.items.all())
            t1 = time.perf_counter()

            n1_count = len(connection.queries)
            n1_ms = (t1 - t0) * 1000

        # --- Benchmark: Optimized ---
        with bind_tenant(tenant):
            reset_queries()

            t0 = time.perf_counter()
            qs = (Order.objects.filter(user=user)
                  .select_related("customer")
                  .prefetch_related("items"))
            for o in qs:
                _ = o.customer.name
                _ = list(o.items.all())
            t1 = time.perf_counter()

            opt_count = len(connection.queries)
            opt_ms = (t1 - t0) * 1000
            connection.force_debug_cursor = False

        # --- Results ---
        self.stdout.write("")
        self.stdout.write(f"  N+1:       {n1_count} queries  {n1_ms:.0f} ms")
        self.stdout.write(f"  Optimized: {opt_count} queries  {opt_ms:.0f} ms")
        self.stdout.write(f"  Reduction: {n1_count/opt_count:.0f}×")
