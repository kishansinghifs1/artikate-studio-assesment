import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from orders.models import Tenant, Customer, Order, OrderItem

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def setup_data(db):
    tenant = Tenant.objects.create(name="Acme Corp", subdomain="acme")
    user = User.objects.create_user(username="acme_user", password="password")
    
    # Create models using all_objects to bypass lack of request tenant context
    customer = Customer.all_objects.create(tenant=tenant, name="Alice", email="alice@acme.com")
    
    order1 = Order.all_objects.create(tenant=tenant, user=user, customer=customer)
    order2 = Order.all_objects.create(tenant=tenant, user=user, customer=customer)
    
    OrderItem.all_objects.create(tenant=tenant, order=order1, sku="SKU-1", quantity=1, price=5.00)
    OrderItem.all_objects.create(tenant=tenant, order=order1, sku="SKU-2", quantity=3, price=15.00)
    OrderItem.all_objects.create(tenant=tenant, order=order2, sku="SKU-3", quantity=1, price=20.00)
    
    return {
        "tenant": tenant,
        "user": user,
        "customer": customer,
        "order1": order1,
        "order2": order2,
    }

def test_view_without_tenant_header_fails_500(api_client, setup_data):
    user = setup_data["user"]
    api_client.force_authenticate(user=user)
    
    from orders.tenant_context import TenantContextMissing
    
    # Without X-Tenant header -> TenantContextMissing raised, verifying database fail-closed
    url = reverse('orders-optimized')
    with pytest.raises(TenantContextMissing):
        api_client.get(url)

def test_view_with_valid_tenant_header_succeeds(api_client, setup_data):
    user = setup_data["user"]
    api_client.force_authenticate(user=user)
    
    url = reverse('orders-optimized')
    response = api_client.get(url, HTTP_X_TENANT="acme")
    
    assert response.status_code == 200
    assert len(response.data) == 2
    
    # Verify exact contents
    assert response.data[0]["customer_name"] == "Alice"
    assert "SKU-1" in response.data[0]["items"]
    assert "SKU-2" in response.data[0]["items"]
    
    # Verify unoptimized view also succeeds if header is set
    url_unopt = reverse('orders-unoptimized')
    response_unopt = api_client.get(url_unopt, HTTP_X_TENANT="acme")
    assert response_unopt.status_code == 200
    assert len(response_unopt.data) == 2
