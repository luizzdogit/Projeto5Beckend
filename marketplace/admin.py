from django.contrib import admin
from .models import Categoria, ItemPedido, Pedido, Produto


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    search_fields = ("nome",)
    list_display = ("nome", "descricao")


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ("nome", "categoria", "preco", "estoque", "vendedor")
    list_filter = ("categoria",)
    search_fields = ("nome", "descricao")

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(vendedor=request.user)

    def get_fields(self, request, obj=None):
        fields = ("nome", "descricao", "preco", "estoque", "categoria")
        if request.user.is_superuser:
            return (*fields, "vendedor")
        return fields

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            obj.vendedor = request.user
        super().save_model(request, obj, form, change)


class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    readonly_fields = ("produto", "quantidade", "preco_unitario")
    can_delete = False


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("id", "comprador", "data", "status", "valor_total")
    list_filter = ("status", "data")
    search_fields = ("comprador__username",)
    readonly_fields = ("comprador", "data", "valor_total")
    inlines = (ItemPedidoInline,)

    def has_add_permission(self, request):
        return False


@admin.register(ItemPedido)
class ItemPedidoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "produto", "quantidade", "preco_unitario")
    readonly_fields = ("pedido", "produto", "quantidade", "preco_unitario")

    def has_add_permission(self, request):
        return False
