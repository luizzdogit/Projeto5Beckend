from decimal import Decimal

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from rest_framework.test import APIClient

from .admin import ProdutoAdmin
from .models import Categoria, ItemPedido, Pedido, Produto


class MarketplaceAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.vendedor = self.make_user("vendedor", is_staff=True)
        self.comprador = self.make_user("comprador")
        self.categoria = Categoria.objects.create(nome="Livros")
        self.produto = Produto.objects.create(
            nome="Livro de backend",
            descricao="Introdução ao desenvolvimento web.",
            preco=Decimal("25.00"),
            estoque=5,
            categoria=self.categoria,
            vendedor=self.vendedor,
        )

    def make_user(self, username, is_staff=False):
        return get_user_model().objects.create_user(
            username=username,
            password="test-password",
            is_staff=is_staff,
        )

    def test_products_are_public_but_product_creation_requires_authentication(self):
        response = self.client.get("/api/products/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["nome"], "Livro de backend")

        response = self.client.post(
            "/api/products/",
            {"nome": "Novo produto"},
            format="json",
        )
        self.assertIn(response.status_code, (401, 403))

        self.client.force_authenticate(self.vendedor)
        response = self.client.post(
            "/api/products/",
            {
                "nome": "Caderno",
                "descricao": "Capa dura",
                "preco": "12.50",
                "estoque": 3,
                "categoria": self.categoria.pk,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["vendedor"], self.vendedor.pk)

    def test_cart_can_add_update_and_remove_product(self):
        response = self.client.post(
            "/api/cart/items/",
            {"produto_id": self.produto.pk, "quantidade": 2},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["itens"][0]["quantidade"], 2)

        response = self.client.patch(
            f"/api/cart/items/{self.produto.pk}/",
            {"quantidade": 3},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["valor_total"], Decimal("75.00"))

        response = self.client.delete(f"/api/cart/items/{self.produto.pk}/")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.get("/api/cart/").data["itens"], [])

    def test_checkout_records_purchase_price_reduces_stock_and_clears_cart(self):
        self.client.post(
            "/api/cart/items/",
            {"produto_id": self.produto.pk, "quantidade": 2},
            format="json",
        )
        Produto.objects.filter(pk=self.produto.pk).update(preco=Decimal("30.00"))
        self.client.force_authenticate(self.comprador)

        response = self.client.post("/api/orders/", {}, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["valor_total"], "60.00")
        item = ItemPedido.objects.get(pedido_id=response.data["id"])
        self.assertEqual(item.preco_unitario, Decimal("30.00"))
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque, 3)
        self.assertEqual(self.client.get("/api/cart/").data["itens"], [])
        self.assertEqual(Pedido.objects.filter(comprador=self.comprador).count(), 1)

    def test_store_pages_render_for_anonymous_visitors(self):
        for path in ("/", "/cart/", "/checkout/", "/accounts/login/"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)

    def test_invalid_checkout_leaves_stock_orders_and_cart_unchanged(self):
        self.client.post(
            "/api/cart/items/",
            {"produto_id": self.produto.pk, "quantidade": 2},
            format="json",
        )
        self.client.force_authenticate(self.comprador)
        Produto.objects.filter(pk=self.produto.pk).update(estoque=1)

        response = self.client.post("/api/orders/", {}, format="json")

        self.assertEqual(response.status_code, 400)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque, 1)
        self.assertFalse(Pedido.objects.exists())
        self.assertEqual(self.client.get("/api/cart/").data["itens"][0]["quantidade"], 2)

    def test_order_list_requires_authentication_and_only_returns_buyers_orders(self):
        response = self.client.get("/api/orders/")
        self.assertIn(response.status_code, (401, 403))

        order = Pedido.objects.create(comprador=self.comprador)
        Pedido.objects.create(comprador=self.vendedor)
        self.client.force_authenticate(self.comprador)

        response = self.client.get("/api/orders/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data], [order.pk])

    def test_admin_product_queryset_is_scoped_to_logged_in_vendor(self):
        another_vendor = self.make_user("outro-vendedor", is_staff=True)
        other_product = Produto.objects.create(
            nome="Outro livro",
            preco=Decimal("10.00"),
            estoque=1,
            categoria=self.categoria,
            vendedor=another_vendor,
        )
        request = RequestFactory().get("/admin/marketplace/produto/")
        request.user = self.vendedor
        product_admin = ProdutoAdmin(Produto, admin.site)

        visible_ids = set(product_admin.get_queryset(request).values_list("pk", flat=True))

        self.assertEqual(visible_ids, {self.produto.pk})
        self.assertNotIn(other_product.pk, visible_ids)
