from django.urls import path

from .api_views import (
    CartItemDetailView,
    CartItemsView,
    CartView,
    OrderListCreateView,
    ProductDetailView,
    ProductListCreateView,
)

urlpatterns = [
    path("products/", ProductListCreateView.as_view(), name="product-list"),
    path("products/<int:pk>/", ProductDetailView.as_view(), name="product-detail"),
    path("cart/", CartView.as_view(), name="cart-detail"),
    path("cart/items/", CartItemsView.as_view(), name="cart-items"),
    path(
        "cart/items/<int:produto_id>/",
        CartItemDetailView.as_view(),
        name="cart-item-detail",
    ),
    path("orders/", OrderListCreateView.as_view(), name="order-list"),
]
