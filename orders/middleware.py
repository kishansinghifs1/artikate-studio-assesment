from .models import Tenant
from .tenant_context import current_tenant


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant = self._resolve_tenant(request)
        token = current_tenant.set(tenant)
        try:
            return self.get_response(request)
        finally:
            current_tenant.reset(token)

    def _resolve_tenant(self, request):
        tenant_id = request.headers.get("X-Tenant")
        if not tenant_id:
            return None
        try:
            return Tenant.objects.get(subdomain=tenant_id)
        except Tenant.DoesNotExist:
            return None
