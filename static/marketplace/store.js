const api = "/api/";
const currency = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});

function csrfToken() {
  return document.querySelector("#csrf-token input[name=csrfmiddlewaretoken]")?.value;
}

async function request(path, options = {}) {
  const headers = { Accept: "application/json", ...options.headers };
  if (options.body) headers["Content-Type"] = "application/json";
  if (options.method && options.method !== "GET") headers["X-CSRFToken"] = csrfToken();
  const response = await fetch(api + path, { ...options, headers, credentials: "same-origin" });
  if (response.status === 204) return null;
  const body = await response.json();
  if (!response.ok) {
    const detail = Object.values(body).flat().join(" ");
    throw new Error(detail || "Não foi possível concluir a operação.");
  }
  return body;
}

function showMessage(text, isError = false) {
  const message = document.querySelector("#message");
  if (!message) return;
  message.textContent = text;
  message.classList.toggle("error", isError);
}

function money(value) {
  return currency.format(Number(value));
}

async function updateCartCount() {
  try {
    const cart = await request("cart/");
    const count = cart.itens.reduce((sum, item) => sum + item.quantidade, 0);
    document.querySelector("#cart-count").textContent = count;
    localStorage.setItem("marketplaceCartCount", String(count));
  } catch (error) {
    document.querySelector("#cart-count").textContent =
      localStorage.getItem("marketplaceCartCount") || "0";
    showMessage(error.message || "Não foi possível atualizar o carrinho.", true);
  }
}

function createProductCard(product) {
  const card = document.createElement("article");
  card.className = "product-card";
  const category = document.createElement("span");
  category.className = "product-category";
  category.textContent = product.categoria_nome;
  const name = document.createElement("h2");
  name.textContent = product.nome;
  const description = document.createElement("p");
  description.className = "product-description";
  description.textContent = product.descricao || "Sem descrição.";
  const meta = document.createElement("div");
  meta.className = "product-meta";
  const price = document.createElement("span");
  price.className = "product-price";
  price.textContent = money(product.preco);
  const stock = document.createElement("span");
  stock.className = "stock";
  stock.textContent = product.estoque > 0 ? `${product.estoque} em estoque` : "Indisponível";
  meta.append(price, stock);
  const button = document.createElement("button");
  button.className = "button";
  button.type = "button";
  button.textContent = product.estoque > 0 ? "Adicionar ao carrinho" : "Sem estoque";
  button.disabled = product.estoque < 1;
  button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      await request("cart/items/", {
        method: "POST",
        body: JSON.stringify({ produto_id: product.id, quantidade: 1 }),
      });
      showMessage(`${product.nome} foi adicionado ao carrinho.`);
      await updateCartCount();
    } catch (error) {
      showMessage(error.message, true);
    } finally {
      button.disabled = product.estoque < 1;
    }
  });
  card.append(category, name, description, meta, button);
  return card;
}

async function loadCatalog() {
  const list = document.querySelector("#products");
  if (!list) return;
  try {
    const products = await request("products/");
    list.replaceChildren();
    if (!products.length) {
      list.textContent = "Ainda não há produtos cadastrados.";
      return;
    }
    products.forEach((product) => list.append(createProductCard(product)));
  } catch (error) {
    list.textContent = "Não foi possível carregar o catálogo.";
    showMessage(error.message, true);
  }
}

function createCartRow(item, onChange, onRemove) {
  const row = document.createElement("article");
  row.className = "cart-row";
  const info = document.createElement("div");
  const name = document.createElement("h2");
  name.textContent = item.produto.nome;
  const price = document.createElement("p");
  price.textContent = `${money(item.produto.preco)} cada`;
  info.append(name, price);
  const quantity = document.createElement("input");
  quantity.type = "number";
  quantity.min = "1";
  quantity.max = String(item.produto.estoque);
  quantity.value = String(item.quantidade);
  quantity.setAttribute("aria-label", `Quantidade de ${item.produto.nome}`);
  quantity.addEventListener("change", () => onChange(item.produto.id, Number(quantity.value)));
  const subtotal = document.createElement("strong");
  subtotal.textContent = money(item.subtotal);
  const remove = document.createElement("button");
  remove.className = "remove-button";
  remove.type = "button";
  remove.textContent = "Remover";
  remove.addEventListener("click", () => onRemove(item.produto.id));
  row.append(info, quantity, subtotal, remove);
  return row;
}

async function loadCart() {
  const list = document.querySelector("#cart-items");
  if (!list) return;
  try {
    const cart = await request("cart/");
    list.replaceChildren();
    if (!cart.itens.length) {
      list.textContent = "Seu carrinho está vazio.";
    } else {
      cart.itens.forEach((item) => list.append(createCartRow(
        item,
        async (productId, quantity) => {
          try {
            if (!Number.isInteger(quantity) || quantity < 1) throw new Error("Informe uma quantidade válida.");
            await request(`cart/items/${productId}/`, {
              method: "PATCH",
              body: JSON.stringify({ quantidade: quantity }),
            });
            await loadCart();
            await updateCartCount();
          } catch (error) {
            showMessage(error.message, true);
            await loadCart();
          }
        },
        async (productId) => {
          try {
            await request(`cart/items/${productId}/`, { method: "DELETE" });
            showMessage("Produto removido do carrinho.");
            await loadCart();
            await updateCartCount();
          } catch (error) {
            showMessage(error.message, true);
          }
        },
      )));
    }
    document.querySelector("#cart-total").textContent = money(cart.valor_total);
  } catch (error) {
    showMessage(error.message, true);
  }
}

async function loadCheckout() {
  const list = document.querySelector("#checkout-items");
  if (!list) return;
  try {
    const cart = await request("cart/");
    list.replaceChildren();
    if (!cart.itens.length) list.textContent = "Seu carrinho está vazio.";
    cart.itens.forEach((item) => {
      const row = document.createElement("article");
      row.className = "cart-row";
      const name = document.createElement("h2");
      name.textContent = `${item.quantidade} × ${item.produto.nome}`;
      const subtotal = document.createElement("strong");
      subtotal.textContent = money(item.subtotal);
      row.append(name, subtotal);
      list.append(row);
    });
    document.querySelector("#checkout-total").textContent = money(cart.valor_total);
    document.querySelector("#place-order").disabled ||= !cart.itens.length;
  } catch (error) {
    showMessage(error.message, true);
  }
}

async function placeOrder() {
  const button = document.querySelector("#place-order");
  button.disabled = true;
  try {
    const order = await request("orders/", { method: "POST", body: JSON.stringify({}) });
    localStorage.setItem("marketplaceLastOrderId", String(order.id));
    showMessage(`Pedido #${order.id} confirmado. Total: ${money(order.valor_total)}.`);
    document.querySelector("#checkout-items").textContent = "Obrigado pela sua compra!";
    document.querySelector("#checkout-total").textContent = money(order.valor_total);
    await updateCartCount();
  } catch (error) {
    showMessage(error.message, true);
    button.disabled = false;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  updateCartCount();
  loadCatalog();
  loadCart();
  loadCheckout();
  document.querySelector("#place-order")?.addEventListener("click", placeOrder);
});
