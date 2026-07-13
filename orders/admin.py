from django.contrib import admin
from .models import Tenant, Customer, Order, OrderItem


# Tenant is a global model — no scoping needed.
admin.site.register(Tenant)


class TenantScopedAdmin(admin.ModelAdmin):
    """Uses all_objects so Django admin works without an active tenant context."""

    def get_queryset(self, request):
        return self.model.all_objects.get_queryset()


admin.site.register(Customer, TenantScopedAdmin)
admin.site.register(Order, TenantScopedAdmin)
admin.site.register(OrderItem, TenantScopedAdmin)
