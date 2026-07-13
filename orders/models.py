from django.db import models
from django.contrib.auth.models import User
from .managers import TenantManager


class Tenant(models.Model):
    name = models.CharField(max_length=100, unique=True)
    subdomain = models.CharField(max_length=100, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Customer(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    email = models.EmailField()

    objects = TenantManager()
    all_objects = models.Manager()

    def __str__(self):
        return self.name


class Order(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    status = models.CharField(max_length=50, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantManager()
    all_objects = models.Manager()

    def __str__(self):
        return f"Order #{self.id}"


class OrderItem(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    sku = models.CharField(max_length=50)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    objects = TenantManager()
    all_objects = models.Manager()

    def __str__(self):
        return f"{self.sku} x {self.quantity}"
