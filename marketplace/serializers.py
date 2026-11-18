from rest_framework import serializers

from .models import Categoria, ItemPedido, Pedido, Produto


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ("id", "nome", "descricao")


class ProdutoSerializer(serializers.ModelSerializer):
    categoria_nome = serializers.CharField(source="categoria.nome", read_only=True)
    vendedor_nome = serializers.CharField(source="vendedor.username", read_only=True)
    vendedor = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Produto
        fields = (
            "id",
            "nome",
            "descricao",
            "preco",
            "estoque",
            "categoria",
            "categoria_nome",
            "vendedor",
            "vendedor_nome",
        )


class ItemPedidoSerializer(serializers.ModelSerializer):
    produto_nome = serializers.CharField(source="produto.nome", read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = ItemPedido
        fields = (
            "id",
            "produto",
            "produto_nome",
            "quantidade",
            "preco_unitario",
            "subtotal",
        )

    def get_subtotal(self, item):
        return item.preco_unitario * item.quantidade


class PedidoSerializer(serializers.ModelSerializer):
    itens = ItemPedidoSerializer(many=True, read_only=True)
    comprador_nome = serializers.CharField(source="comprador.username", read_only=True)

    class Meta:
        model = Pedido
        fields = (
            "id",
            "comprador",
            "comprador_nome",
            "data",
            "status",
            "valor_total",
            "itens",
        )
        read_only_fields = fields


class AdicionarItemCarrinhoSerializer(serializers.Serializer):
    produto_id = serializers.IntegerField(min_value=1)
    quantidade = serializers.IntegerField(min_value=1, default=1)


class AtualizarItemCarrinhoSerializer(serializers.Serializer):
    quantidade = serializers.IntegerField(min_value=1)
