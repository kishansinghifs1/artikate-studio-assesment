from django.db import models
from contextlib import contextmanager
from .tenant_context import current_tenant, TenantContextMissing


class TenantManager(models.Manager):
    """Scopes all queries to the current tenant. Raises if no tenant is set."""

    def get_queryset(self):
        tenant = current_tenant.get()
        if tenant is None:
            raise TenantContextMissing("No tenant in context")
        return super().get_queryset().filter(tenant=tenant)


@contextmanager
def bind_tenant(tenant):
    token = current_tenant.set(tenant)
    try:
        yield tenant
    finally:
        current_tenant.reset(token)
