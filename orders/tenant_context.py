import contextvars


current_tenant = contextvars.ContextVar("current_tenant", default=None)


class TenantContextMissing(Exception):
    pass
