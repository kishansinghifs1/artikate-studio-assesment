from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Order


class OrderSummaryUnoptimizedView(APIView):
    """The broken view — no select_related/prefetch_related, so it fires N+1 queries."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(user=request.user)
        data = []
        for o in orders:
            data.append({
                "id": o.id,
                "customer_name": o.customer.name,
                "items": [i.sku for i in o.items.all()],
            })
        return Response(data)


class OrderSummaryOptimizedView(APIView):
    """The fixed view — select_related joins customer, prefetch_related batches items."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = (
            Order.objects
            .filter(user=request.user)
            .select_related("customer")
            .prefetch_related("items")
        )
        data = []
        for o in orders:
            data.append({
                "id": o.id,
                "customer_name": o.customer.name,
                "items": [i.sku for i in o.items.all()],
            })
        return Response(data)
