# Marketplace Simplificado — IESB

Projeto acadêmico de marketplace com catálogo de produtos, vendedores, compradores, carrinho em sessão, pedidos e API REST. O checkout valida o estoque, registra o preço vigente de cada produto e reduz o estoque dentro de uma transação atômica.

## Tecnologias

- Python 3.13
- Django 5.2
- Django REST Framework 3.16
- SQLite
- HTML, CSS e JavaScript (Fetch API)

## Funcionalidades principais

- Cadastro de categorias, produtos, pedidos e itens de pedido.
- Usuários nativos do Django como compradores e vendedores.
- Admin: cada vendedor staff visualiza e gerencia apenas os próprios produtos; superusuários podem gerenciar todos.
- Carrinho persistido na sessão do Django, com inclusão, atualização e remoção de itens.
- Checkout autenticado com validação completa do estoque, preço unitário histórico, atualização de estoque, criação de pedido e limpeza do carrinho em transação atômica.
- Catálogo, carrinho e checkout em páginas responsivas; o servidor mantém o carrinho e o `localStorage` guarda informações auxiliares da interface.

## Instalação e execução

No PowerShell, na pasta do projeto:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Abra `http://127.0.0.1:8000/` para o catálogo e `http://127.0.0.1:8000/admin/` para o painel administrativo. Para atuar como vendedor no Admin, o usuário deve ter acesso de staff. Categorias podem ser cadastradas pelo Admin; um vendedor cria seus produtos associados a uma categoria. Compradores devem entrar em `/accounts/login/` para finalizar pedidos.

Para produção, defina `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0` e `DJANGO_ALLOWED_HOSTS` no ambiente. A chave padrão do projeto é apenas para desenvolvimento local.

## Endpoints da API

| Método | Endpoint | Acesso | Descrição |
|---|---|---|---|
| `GET` | `/api/products/` | Público | Lista produtos |
| `POST` | `/api/products/` | Autenticado | Cadastra produto para o usuário autenticado |
| `GET` | `/api/products/<id>/` | Público | Consulta um produto |
| `GET` | `/api/cart/` | Público | Consulta o carrinho da sessão |
| `POST` | `/api/cart/items/` | Público | Adiciona `{ "produto_id": 1, "quantidade": 2 }` |
| `PATCH` | `/api/cart/items/<id>/` | Público | Atualiza `{ "quantidade": 3 }` |
| `DELETE` | `/api/cart/items/<id>/` | Público | Remove um item |
| `GET` | `/api/orders/` | Autenticado | Lista somente os pedidos do usuário autenticado |
| `POST` | `/api/orders/` | Autenticado | Finaliza o carrinho atual e cria um pedido |

As operações protegidas usam a autenticação de sessão do Django (ou Basic Authentication para clientes de API). Requisições de escrita autenticadas por sessão devem enviar o token CSRF (`X-CSRFToken`).

## Validação

Executado durante o desenvolvimento:

```powershell
python manage.py check
python manage.py makemigrations marketplace
python manage.py migrate
python manage.py test marketplace
```

A suíte cobre cadastro e permissões da API de produtos, isolamento dos pedidos por comprador, operações do carrinho, checkout bem-sucedido e rejeição de checkout sem estoque sem alteração parcial do estoque ou do pedido.
