from django.urls import path
from .views import OrderSummaryUnoptimizedView, OrderSummaryOptimizedView

urlpatterns = [
    path('orders/unoptimized/', OrderSummaryUnoptimizedView.as_view(), name='orders-unoptimized'),
    path('orders/optimized/', OrderSummaryOptimizedView.as_view(), name='orders-optimized'),
]
