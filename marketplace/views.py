from django.shortcuts import render


def catalog_page(request):
    return render(request, "marketplace/catalog.html")


def cart_page(request):
    return render(request, "marketplace/cart.html")


def checkout_page(request):
    return render(request, "marketplace/checkout.html")
