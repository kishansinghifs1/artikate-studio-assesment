import pytest
from django.contrib.auth.models import User
from orders.models import Tenant, Customer, Order, OrderItem
from orders.tenant_context import TenantContextMissing, current_tenant
from orders.managers import bind_tenant

@pytest.fixture
def db_setup(db):
    """
    Sets up two tenants, their customers, and their orders.
    """
    # Create tenants
    tenant_a = Tenant.objects.create(name="Tenant A", subdomain="tenant-a")
    tenant_b = Tenant.objects.create(name="Tenant B", subdomain="tenant-b")

    # Create users
    user = User.objects.create_user(username="testuser", password="password")

    # Create customers (must bypass TenantManager to create directly without active context)
    customer_a = Customer.all_objects.create(tenant=tenant_a, name="Customer A", email="a@test.com")
    customer_b = Customer.all_objects.create(tenant=tenant_b, name="Customer B", email="b@test.com")

    # Create orders
    order_a = Order.all_objects.create(tenant=tenant_a, user=user, customer=customer_a, status="pending")
    order_b = Order.all_objects.create(tenant=tenant_b, user=user, customer=customer_b, status="completed")

    # Create order items
    OrderItem.all_objects.create(tenant=tenant_a, order=order_a, sku="SKU-A1", quantity=2, price=10.00)
    OrderItem.all_objects.create(tenant=tenant_b, order=order_b, sku="SKU-B1", quantity=1, price=20.00)

    return {
        "tenant_a": tenant_a,
        "tenant_b": tenant_b,
        "user": user,
        "customer_a": customer_a,
        "customer_b": customer_b,
        "order_a": order_a,
        "order_b": order_b,
    }

def test_missing_context_raises(db_setup):
    """Test that queries without a tenant context raise TenantContextMissing."""
    # Assert current tenant context is indeed None
    assert current_tenant.get() is None

    # Assert that queries on default managers fail-closed by raising TenantContextMissing
    with pytest.raises(TenantContextMissing):
        list(Order.objects.all())

    with pytest.raises(TenantContextMissing):
        list(Customer.objects.all())

    with pytest.raises(TenantContextMissing):
        list(OrderItem.objects.all())

def test_tenant_a_cannot_see_tenant_b_orders(db_setup):
    """Test that a tenant cannot access another tenant's data."""
    tenant_a = db_setup["tenant_a"]
    order_b = db_setup["order_b"]

    with bind_tenant(tenant_a):
        # Assert Tenant B's order is not visible under Tenant A's context
        qs = Order.objects.filter(id=order_b.id)
        assert len(qs) == 0
        assert not qs.exists()

def test_objects_all_is_scoped(db_setup):
    """Test that .objects.all() is scoped to the current tenant."""
    tenant_a = db_setup["tenant_a"]
    order_a = db_setup["order_a"]

    with bind_tenant(tenant_a):
        orders = list(Order.objects.all())
        assert len(orders) == 1
        assert orders[0].id == order_a.id
        assert orders[0].tenant == tenant_a

def test_all_objects_bypasses_intentionally(db_setup):
    """Test that .all_objects bypasses tenant scoping."""
    # Without binding any tenant context, using the escape hatch should work
    assert current_tenant.get() is None
    
    all_orders = list(Order.all_objects.all())
    assert len(all_orders) == 2

    # Bind Tenant A, but verify all_objects still sees Tenant B's order
    tenant_a = db_setup["tenant_a"]
    with bind_tenant(tenant_a):
        all_orders_scoped = list(Order.all_objects.all())
        assert len(all_orders_scoped) == 2
