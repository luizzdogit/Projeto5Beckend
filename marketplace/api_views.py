from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ItemPedido, Pedido, Produto
from .serializers import (
    AdicionarItemCarrinhoSerializer,
    AtualizarItemCarrinhoSerializer,
    PedidoSerializer,
    ProdutoSerializer,
)

CART_SESSION_KEY = "marketplace_cart"


class ProductListCreateView(generics.ListCreateAPIView):
    queryset = Produto.objects.select_related("categoria", "vendedor").all()
    serializer_class = ProdutoSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def perform_create(self, serializer):
        serializer.save(vendedor=self.request.user)


class ProductDetailView(generics.RetrieveAPIView):
    queryset = Produto.objects.select_related("categoria", "vendedor").all()
    serializer_class = ProdutoSerializer
    permission_classes = (permissions.AllowAny,)


def get_cart(request):
    cart = request.session.get(CART_SESSION_KEY, {})
    if not isinstance(cart, dict):
        raise ValidationError({"carrinho": "O conteúdo do carrinho é inválido."})
    normalized = {}
    try:
        for product_id, quantity in cart.items():
            product_id = int(product_id)
            quantity = int(quantity)
            if product_id < 1 or quantity < 1:
                raise ValueError
            normalized[str(product_id)] = quantity
    except (TypeError, ValueError):
        raise ValidationError({"carrinho": "O conteúdo do carrinho é inválido."})
    return normalized


def serialize_cart(cart):
    product_ids = [int(product_id) for product_id in cart]
    products = Produto.objects.select_related("categoria").in_bulk(product_ids)
    missing_ids = set(product_ids) - set(products)
    if missing_ids:
        raise ValidationError(
            {"carrinho": "Um ou mais produtos do carrinho não estão mais disponíveis."}
        )

    items = []
    total = Decimal("0.00")
    for product_id, quantity in cart.items():
        product = products[int(product_id)]
        subtotal = product.preco * quantity
        total += subtotal
        items.append(
            {
                "produto": ProdutoSerializer(product).data,
                "quantidade": quantity,
                "subtotal": subtotal,
            }
        )
    return {"itens": items, "valor_total": total}


class CartView(APIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        return Response(serialize_cart(get_cart(request)))


class CartItemsView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = AdicionarItemCarrinhoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product_id = serializer.validated_data["produto_id"]
        quantity = serializer.validated_data["quantidade"]
        product = get_object_or_404(Produto, pk=product_id)
        cart = get_cart(request)
        new_quantity = cart.get(str(product_id), 0) + quantity
        if new_quantity > product.estoque:
            raise ValidationError(
                {"quantidade": f"Estoque disponível: {product.estoque}."}
            )
        cart[str(product_id)] = new_quantity
        request.session[CART_SESSION_KEY] = cart
        return Response(serialize_cart(cart), status=status.HTTP_200_OK)


class CartItemDetailView(APIView):
    permission_classes = (permissions.AllowAny,)

    def patch(self, request, produto_id):
        serializer = AtualizarItemCarrinhoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart = get_cart(request)
        product_key = str(produto_id)
        if product_key not in cart:
            raise ValidationError({"produto_id": "O produto não está no carrinho."})
        product = get_object_or_404(Produto, pk=produto_id)
        quantity = serializer.validated_data["quantidade"]
        if quantity > product.estoque:
            raise ValidationError(
                {"quantidade": f"Estoque disponível: {product.estoque}."}
            )
        cart[product_key] = quantity
        request.session[CART_SESSION_KEY] = cart
        return Response(serialize_cart(cart))

    def delete(self, request, produto_id):
        cart = get_cart(request)
        cart.pop(str(produto_id), None)
        request.session[CART_SESSION_KEY] = cart
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrderListCreateView(generics.ListAPIView):
    serializer_class = PedidoSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return (
            Pedido.objects.filter(comprador=self.request.user)
            .prefetch_related("itens__produto")
        )

    @transaction.atomic
    def post(self, request):
        cart = get_cart(request)
        if not cart:
            raise ValidationError({"carrinho": "O carrinho está vazio."})

        product_ids = [int(product_id) for product_id in cart]
        products = Produto.objects.select_for_update().in_bulk(product_ids)
        if len(products) != len(cart):
            raise ValidationError(
                {"carrinho": "Um ou mais produtos do carrinho não estão mais disponíveis."}
            )

        for product_id, quantity in cart.items():
            product = products[int(product_id)]
            if quantity > product.estoque:
                raise ValidationError(
                    {
                        "estoque": (
                            f"Estoque insuficiente para {product.nome}. "
                            f"Disponível: {product.estoque}."
                        )
                    }
                )

        total = sum(
            (products[int(product_id)].preco * quantity for product_id, quantity in cart.items()),
            Decimal("0.00"),
        )
        order = Pedido.objects.create(comprador=request.user, valor_total=total)
        items = []
        for product_id, quantity in cart.items():
            product = products[int(product_id)]
            items.append(
                ItemPedido(
                    pedido=order,
                    produto=product,
                    quantidade=quantity,
                    preco_unitario=product.preco,
                )
            )
            product.estoque -= quantity
            product.save(update_fields=("estoque",))
        ItemPedido.objects.bulk_create(items)
        request.session.pop(CART_SESSION_KEY, None)
        return Response(PedidoSerializer(order).data, status=status.HTTP_201_CREATED)
