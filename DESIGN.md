# System Architecture Design

This document details the architectural decisions and design patterns used in the Artikate Studio Backend Assessment.

---

## 1. Multi-Tenant Isolation (Section 3)

We implement **Shared Database, Shared Schema** multi-tenancy. This is the most cost-effective and operationally simple pattern, but it requires absolute query isolation at the application layer.

### Context Management via `contextvars`
Tenant context is held in a request-scoped `contextvars.ContextVar("current_tenant")` rather than `threading.local()`. 

- **The Problem with Thread-Locals**: In modern ASGI / async Django configurations, a single OS thread can interleave execution of multiple concurrent asynchronous tasks (coroutines). A thread-local variable set during request A will leak into request B if request B runs on the same thread during an `await` pause.
- **The Solution**: Python's `contextvars` module is designed for async-safety. Coroutines copy context variables upon creation, preventing cross-request leaks.

### Fail-Closed Database Manager
Our custom `TenantManager(models.Manager)` overrides `get_queryset()` to enforce isolation:

```python
def get_queryset(self):
    tenant = current_tenant.get()
    if tenant is None:
        raise TenantContextMissing("No tenant bound — refusing to return unscoped queryset")
    return super().get_queryset().filter(tenant=tenant)
```

- **Fail-Closed Principle**: If no tenant is explicitly bound (e.g., a developer forgets to include the tenant middleware, or calls a query from a background thread/task without binding), the system **raises an exception** instead of returning unfiltered global records.
- **Escape Hatch**: To support administrative, cross-tenant, or migration workflows, we explicitly register `all_objects = models.Manager()` on all tenant models.

---

## 2. Rate-Limited Job Queue (Section 2)

We implement a rate-limited task queue using **Celery + Redis** with a **Sliding Window Log** rate limiter implemented via a Redis pipeline.

### Architecture Comparison

| Architecture | Pros | Cons |
| :--- | :--- | :--- |
| **Celery + Redis** (Chosen) | Mature retry/backoff mechanism, built-in task routing, dead-letter options, horizontal scaling, crash safety via `acks_late`. | Operational overhead (requires running workers and a message broker). Redis is a SPOF unless clustered. |
| **Django-Q** | Simple setup, Django-native DB or Redis backend. | Smaller ecosystem, weaker retry/backoff ergonomics, less battle-tested at scale. |
| **Custom DB-Polling** | No extra infrastructure dependencies. | High database contention under burst loads, poor polling latency, difficult to implement correct distributed locking and retries. |

### Lua-Based Sliding Window Rate Limiter
The rate limiter uses a Redis **Sorted Set (ZSET)**.
- **Why Lua over Redis Pipelines?**
  A standard Python `redis.pipeline()` executes commands sequentially in a `MULTI/EXEC` block but does not allow server-side conditional branching (i.e. checking `if count < limit` and *then* executing `ZADD` within the same transaction). This creates a TOCTOU (Time-Of-Check to Time-Of-Use) race condition. 
  By embedding a Lua script inside Python via `redis.register_script()`, the logic executes **atomically and synchronously** inside Redis's single-threaded event loop. This ensures perfect strict rate limiting with zero race conditions, while keeping the codebase to a single clean Python file.
- **Collision Protection**:
  Requests within the same millisecond are protected from overwriting each other in the `ZSET` by appending the current set cardinality (`current_count`) to the member value (`timestamp:count`).

### Fail-Closed Redis Connection
If Redis goes down, the rate limiter raises a `RedisError`. The Celery task catches this exception and **fails closed**—refusing to send the email and immediately scheduling a task retry with exponential backoff. This prevents violating external API rate limits.
