
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from .models import Product, Order, CartItem,Notification
from django.core.paginator import Paginator
from django.urls import reverse
from django.contrib import messages
from decimal import Decimal
import json
from django.http import JsonResponse





# 🏠 DASHBOARD = FEED
@never_cache
@login_required
def dashboard(request):
    query = request.GET.get("q")

    # ⚡ FIX: remove N+1 query problem
    products = Product.objects.select_related('owner').all().order_by("-id")

    if query:
        products = products.filter(title__icontains=query)


    paginator = Paginator(products, 12)
    page = request.GET.get("page")
    products = paginator.get_page(page)

    return render(request, "listings/dashboard.html", {
        "products": products
    })

# ADD PRODUCT

@login_required
def add_product(request):
    if request.method == "POST":

        image = request.FILES.get("image")

        print("FILES:", request.FILES)   # 🔍 DEBUG (temporary)

        product = Product(
            owner=request.user,
            title=request.POST.get("title"),
            description=request.POST.get("description"),
            category=request.POST.get("category"),
            price=request.POST.get("price") or 0,
            stock=request.POST.get("stock") or 0,
        )

        if image:
            product.image = image

        product.save()

        return redirect("listings:dashboard")

    return render(request, "listings/add_product.html")
@login_required
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if product.owner != request.user:
        return redirect("listings:dashboard")

    product.delete()
    return redirect("listings:dashboard")


@login_required
def add_to_cart(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if product.owner == request.user:
        messages.error(request, "You can't add your own product")
        return redirect("listings:dashboard")

    item, created = CartItem.objects.get_or_create(
        user=request.user,
        product=product
    )

    if created:
        messages.success(request, "Added to cart")
    else:
        messages.info(request, "Already in cart")

 
    if request.GET.get("buy_now") == "1":
        return redirect("listings:cart")

    return redirect("listings:dashboard")
@login_required
def update_cart(request, pk, action):
    item = get_object_or_404(CartItem, pk=pk, user=request.user)

    if action == "inc":
        item.quantity += 1
        item.save()

    elif action == "dec":
        if item.quantity > 1:
            item.quantity -= 1
            item.save()
        else:
            item.delete()

    # 🔥 RE-CALCULATE TOTAL AFTER UPDATE
    cart_items = CartItem.objects.filter(user=request.user)

    total = sum(i.product.price * i.quantity for i in cart_items if i.product.price)

    return JsonResponse({
        "deleted": item.quantity == 0,
        "quantity": item.quantity if item.pk else 0,
        "item_id": pk,
        "total": float(total)
    })
@login_required
def remove_from_cart(request, pk):
    item = get_object_or_404(CartItem, pk=pk, user=request.user)
    item.delete()
    return redirect("listings:cart")


@login_required
def cart_view(request):
    cart_items = CartItem.objects.filter(user=request.user).select_related("product")

    total = Decimal("0.00")

    for item in cart_items:
        if item.product.price:
            total += item.product.price * item.quantity

    return render(request, "listings/cart.html", {
        "cart_items": cart_items,
        "total": total
    })


@login_required
def buy_product(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if product.owner == request.user:
        return redirect("listings:dashboard")

    return render(request, "listings/checkout.html", {
        "product": product
    })

@login_required
def checkout(request):
    cart_items = CartItem.objects.filter(user=request.user).select_related("product")

    if not cart_items.exists():
        return redirect("listings:cart")

    total = sum(i.product.price * i.quantity for i in cart_items)

    return render(request, "listings/checkout.html", {
        "cart_items": cart_items,
        "total": total
    })


@login_required
def place_order_cart(request):

    if request.method != "POST":
        return JsonResponse({"success": False, "message": "POST required"})

    # ✅ SAFE JSON PARSE (MAIN FIX)
    try:
        data = json.loads(request.body.decode("utf-8") or "{}")
    except:
        data = {}

    address = data.get("address", "")
    payment = data.get("payment_method", "cod")

    cart_items = CartItem.objects.filter(user=request.user)

    single_product_id = data.get("product_id")

    last_order_id = None

    # =========================
    # BUY NOW FLOW
    # =========================
    if single_product_id:
        product = get_object_or_404(Product, id=single_product_id)

        order = Order.objects.create(
            buyer=request.user,
            product=product,
            quantity=1,
            address=address or "Not provided",
            payment_method=payment,
            status="pending"
        )

        Notification.objects.create(
            user=product.owner,
            message=f"New order: {product.title}"
        )

        last_order_id = order.id

    # =========================
    # CART FLOW
    # =========================
    else:

        if not cart_items.exists():
            return JsonResponse({"success": False, "message": "Cart empty"})

        for item in cart_items:

            order = Order.objects.create(
                buyer=request.user,
                product=item.product,
                quantity=item.quantity,
                address=address or "Not provided",
                payment_method=payment,
                status="pending"
            )

            Notification.objects.create(
                user=item.product.owner,
                message=f"New order: {item.product.title}"
            )

            last_order_id = order.id

        cart_items.delete()

    return JsonResponse({
        "success": True,
        "order_id": last_order_id
    })
# 📦 PRODUCT DETAIL
@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)

    return render(request, "listings/detail.html", {
        "product": product
    })
def order_detail(request, pk):

    o = Order.objects.get(id=pk, buyer=request.user)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":

        return JsonResponse({
            "id": o.id,
            "product": o.product.title,
            "status": o.status,
            "quantity": o.quantity,
            "address": o.address,
            "price": o.product.price
        })

    return render(request, "listings/order_detail.html", {"order": o})

def order_history(request):

    orders = Order.objects.filter(buyer=request.user)

    # AJAX request হলে JSON পাঠাও
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":

        data = list(orders.values("id", "status", "product__title"))
        return JsonResponse(data, safe=False)

    return render(request, "listings/orders.html", {"orders": orders})

@login_required
def my_orders(request):
    orders = Order.objects.filter(
        buyer=request.user
    ).exclude(status="cancelled").select_related("product").order_by("-created_at")

    return render(request, "listings/my_orders.html", {
        "orders": orders
    })

@login_required
def cancel_order(request, pk):

    try:
        order = Order.objects.get(id=pk, buyer=request.user)

        if order.status == "cancelled":
            return JsonResponse({
                "success": False,
                "message": "Already cancelled"
            })

        # ✅ CHANGE STATUS instead of delete
        order.status = "cancelled"
        order.save()

        return JsonResponse({
            "success": True,
            "id": pk
        })

    except Order.DoesNotExist:
        return JsonResponse({
            "success": False,
            "message": "Order not found"
        })
@login_required
def notifications_view(request):

        notifications = Notification.objects.filter(
            user=request.user
        ).order_by("-created_at")

        # mark as read
        notifications.update(is_read=True)

        return render(request, "listings/notifications.html", {
            "notifications": notifications
        })



from django.contrib.auth import get_user_model
from accounts.models import Profile

User = get_user_model()

@login_required
def userProfileView(request, id):
    user_obj = get_object_or_404(User, id=id)

    profile = Profile.objects.filter(user=user_obj).first()

    return render(request, 'listings/userProfile.html', {
        "user_obj": user_obj,
        "profile": profile
    })



@login_required
def userMessage(request,id):

    return render(request, 'listings/messages.html',{"id":id})

