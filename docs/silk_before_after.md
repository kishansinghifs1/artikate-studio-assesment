# Database Query Performance Report (N+1 Profiling)

This document provides profiler evidence showing the regression analysis of the `/api/orders/unoptimized/` endpoint compared to the optimized `/api/orders/optimized/` endpoint.

## Benchmark Configuration
- **Dataset Size**: 250 orders, 1 customer, 750 order items (3 items per order).
- **Tenant Scope**: Tenant context bound via `X-Tenant` middleware header.
- **ORM Optimization**: `select_related('customer')` and `prefetch_related('items')`.

## Query Performance Comparison

| Metric | Unoptimized View (N+1) | Optimized View (Joined/Prefetched) | Improvement |
| :--- | :--- | :--- | :--- |
| **Total Query Count** | 501 queries | 2 queries | **250.5x reduction** |
| **Execution Duration** | 1158.21 ms | 97.10 ms | **11.9x faster** |

---

## Detailed Analysis

### 1. Unoptimized Query Log (N+1 Regression)
The unoptimized view retrieves orders matching the user (`SELECT ... FROM orders_order WHERE user_id = ...`).
Then, it loops over each order, executing two separate SQL queries:
1. Fetch the customer details: `SELECT ... FROM orders_customer WHERE id = <customer_id>`
2. Fetch the associated order items: `SELECT ... FROM orders_orderitem WHERE order_id = <order_id>`

For $N$ orders, this results in $1 + 2N$ database roundtrips.
With 250 orders: $1 + 2(250) = 501$ queries.

#### Sample Queries executed (first few of 501):
- `SELECT "orders_order"."id", "orders_order"."tenant_id", "orders_order"."user_id", "orders_order"."customer_id", "orders_`
- `SELECT "orders_customer"."id", "orders_customer"."tenant_id", "orders_customer"."name", "orders_customer"."email" FROM "`
- `SELECT "orders_orderitem"."id", "orders_orderitem"."tenant_id", "orders_orderitem"."order_id", "orders_orderitem"."sku",`
- `SELECT "orders_customer"."id", "orders_customer"."tenant_id", "orders_customer"."name", "orders_customer"."email" FROM "`
- `SELECT "orders_orderitem"."id", "orders_orderitem"."tenant_id", "orders_orderitem"."order_id", "orders_orderitem"."sku",`
- `SELECT "orders_customer"."id", "orders_customer"."tenant_id", "orders_customer"."name", "orders_customer"."email" FROM "`
... (remaining 495 queries omitted for brevity)

### 2. Optimized Query Log
The optimized view uses:
1. `select_related('customer')` which performs an inner/left SQL join to fetch order and customer records in a single query.
2. `prefetch_related('items')` which performs a second query fetching all items whose order ID belongs to the set of retrieved orders: `SELECT ... FROM orders_orderitem WHERE order_id IN (...)`.

This reduces database roundtrips to exactly **2 queries**, regardless of how many orders are returned ($N$).

#### All Queries executed (exactly 2):
- `SELECT "orders_order"."id", "orders_order"."tenant_id", "orders_order"."user_id", "orders_order"."customer_id", "orders_`
- `SELECT "orders_orderitem"."id", "orders_orderitem"."tenant_id", "orders_orderitem"."order_id", "orders_orderitem"."sku",`
